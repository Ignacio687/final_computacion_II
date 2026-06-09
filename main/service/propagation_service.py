"""Servicio de propagación: maneja mensajes entrantes y reenvía cuando corresponde."""

import asyncio

from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.domain.models.message import Message, MessageType
from main.domain.models.node_info import NodeInfo
from main.domain.models.payloads import (
    ChainResponsePayload,
    GetChainPayload,
    GetMempoolPayload,
    MempoolResponsePayload,
    NewBlockPayload,
    NewTxPayload,
)
from main.infrastructure.validation.block_validator import (
    DefaultBlockValidator,
    balances_from_chain,
)
from main.infrastructure.validation.chain_verification_dispatcher import (
    ChainVerificationDispatcher,
)
from main.repository.dto.mappers import block_from_dto, block_to_dto, transaction_from_dto, transaction_to_dto


class PropagationService:
    def __init__(
        self,
        blockchain_repository: IBlockchainRepository,
        transaction_repository: ITransactionRepository,
        transaction_validator: ITransactionValidator,
        block_validator: IBlockValidator,
        chain_dispatcher: ChainVerificationDispatcher,
        message_sender: IMessageSender,
        chain_lock: asyncio.Lock,
    ) -> None:
        self._blockchain_repository = blockchain_repository
        self._transaction_repository = transaction_repository
        self._transaction_validator = transaction_validator
        self._block_validator = block_validator
        self._chain_dispatcher = chain_dispatcher
        self._message_sender = message_sender
        self._chain_lock = chain_lock

    async def handle_message(self, peer: NodeInfo, message: Message) -> None:
        if message.type == MessageType.NEW_TX:
            await self._handle_new_tx(peer, message)
        elif message.type == MessageType.NEW_BLOCK:
            await self._handle_new_block(peer, message)
        elif message.type == MessageType.GET_CHAIN:
            await self._handle_get_chain(peer, message)
        elif message.type == MessageType.CHAIN_RESPONSE:
            await self._handle_chain_response(message)
        elif message.type == MessageType.GET_MEMPOOL:
            await self._handle_get_mempool(peer)
        elif message.type == MessageType.MEMPOOL_RESPONSE:
            await self._handle_mempool_response(message)

    async def _handle_new_tx(self, peer: NodeInfo, message: Message) -> None:
        if not isinstance(message.payload, NewTxPayload):
            return
        tx = transaction_from_dto(message.payload.transaction)
        async with self._chain_lock:
            if self._transaction_repository.exists_in_mempool_or_chain(tx.id):
                return
            if not self._transaction_validator.validate(tx):
                return
            self._transaction_repository.add_to_mempool(tx)
        await self._message_sender.broadcast(
            Message(
                type=MessageType.NEW_TX,
                payload=NewTxPayload(transaction=transaction_to_dto(tx)),
            ),
            exclude_node_id=peer.node_id,
        )

    async def _handle_new_block(self, peer: NodeInfo, message: Message) -> None:
        if not isinstance(message.payload, NewBlockPayload):
            return
        block = block_from_dto(message.payload.block)
        block_valid = False
        needs_chain_sync = False
        async with self._chain_lock:
            local_height = self._blockchain_repository.get_height()
            if block.id < local_height:
                return
            last_block = self._blockchain_repository.get_last_block()
            if last_block is None:
                return
            if block.id == last_block.id and block.hash == last_block.hash:
                return
            if block.id == local_height and block.hash != last_block.hash:
                needs_chain_sync = True
                return

            previous_hash = last_block.hash
            if block.id == last_block.id + 1:
                if isinstance(self._block_validator, DefaultBlockValidator):
                    balances = balances_from_chain(
                        self._blockchain_repository.get_chain()
                    )
                    block_valid = self._block_validator.validate_with_balances(
                        block,
                        previous_hash,
                        balances,
                        previous_timestamp=last_block.timestamp,
                    )
                else:
                    block_valid = self._block_validator.validate(block, previous_hash)

            if block_valid:
                tip = self._blockchain_repository.get_last_block()
                if (
                    tip is None
                    or tip.id != last_block.id
                    or tip.hash != last_block.hash
                ):
                    return
                if not self._blockchain_repository.append_block(block):
                    block_valid = False
                else:
                    tx_ids = [tx.id for tx in block.transactions]
                    self._transaction_repository.remove_from_mempool(tx_ids)
            elif block.id >= local_height and block.last_hash != previous_hash:
                needs_chain_sync = True
            else:
                return

        if needs_chain_sync:
            await self._request_chain(peer)
            return

        if block_valid:
            await self._message_sender.broadcast(
                Message(
                    type=MessageType.NEW_BLOCK,
                    payload=NewBlockPayload(block=block_to_dto(block)),
                ),
                exclude_node_id=peer.node_id,
            )

    async def _request_chain(self, peer: NodeInfo) -> None:
        await self._message_sender.send_to_peer(
            peer,
            Message(
                type=MessageType.GET_CHAIN,
                payload=GetChainPayload(since_height=0),
            ),
        )

    async def _handle_get_chain(self, peer: NodeInfo, message: Message) -> None:
        if not isinstance(message.payload, GetChainPayload):
            return
        blocks = self._blockchain_repository.get_chain_since(
            message.payload.since_height
        )
        await self._message_sender.send_to_peer(
            peer,
            Message(
                type=MessageType.CHAIN_RESPONSE,
                payload=ChainResponsePayload(
                    blocks=[block_to_dto(block) for block in blocks]
                ),
            ),
        )

    async def _handle_chain_response(self, message: Message) -> None:
        if not isinstance(message.payload, ChainResponsePayload):
            return
        blocks = [block_from_dto(dto) for dto in message.payload.blocks]
        local_height = self._blockchain_repository.get_height()
        if not blocks or blocks[-1].id <= local_height:
            return
        if not await self._chain_dispatcher.verify(blocks):
            return
        async with self._chain_lock:
            local_height = self._blockchain_repository.get_height()
            if not blocks or blocks[-1].id <= local_height:
                return
            self._blockchain_repository.replace_chain(
                blocks,
                tx_reinsert_filter=self._transaction_validator.validate,
            )
            invalid_ids = [
                tx.id
                for tx in self._transaction_repository.get_mempool()
                if not self._transaction_validator.validate(tx)
            ]
            if invalid_ids:
                self._transaction_repository.remove_from_mempool(invalid_ids)

    async def _handle_get_mempool(self, peer: NodeInfo) -> None:
        mempool = self._transaction_repository.get_mempool()
        await self._message_sender.send_to_peer(
            peer,
            Message(
                type=MessageType.MEMPOOL_RESPONSE,
                payload=MempoolResponsePayload(
                    transactions=[transaction_to_dto(tx) for tx in mempool]
                ),
            ),
        )

    async def _handle_mempool_response(self, message: Message) -> None:
        if not isinstance(message.payload, MempoolResponsePayload):
            return
        async with self._chain_lock:
            for dto in message.payload.transactions:
                tx = transaction_from_dto(dto)
                if self._transaction_repository.exists_in_mempool_or_chain(tx.id):
                    continue
                if self._transaction_validator.validate(tx):
                    self._transaction_repository.add_to_mempool(tx)
