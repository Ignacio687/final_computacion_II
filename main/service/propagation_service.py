"""Servicio de propagación: maneja mensajes entrantes y reenvía cuando corresponde."""

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
from main.infrastructure.validation.chain_verification_dispatcher import (
    ChainVerificationDispatcher,
)
from main.repository.dto.mappers import block_from_dto, block_to_dto, transaction_from_dto, transaction_to_dto


class PropagationService:
    """Despacha cada mensaje entrante por tipo."""

    def __init__(
        self,
        blockchain_repository: IBlockchainRepository,
        transaction_repository: ITransactionRepository,
        transaction_validator: ITransactionValidator,
        block_validator: IBlockValidator,
        chain_dispatcher: ChainVerificationDispatcher,
        message_sender: IMessageSender,
    ) -> None:
        self._blockchain_repository = blockchain_repository
        self._transaction_repository = transaction_repository
        self._transaction_validator = transaction_validator
        self._block_validator = block_validator
        self._chain_dispatcher = chain_dispatcher
        self._message_sender = message_sender

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
        local_height = self._blockchain_repository.get_height()
        if block.id < local_height:
            return
        last_block = self._blockchain_repository.get_last_block()
        if last_block is None:
            return
        if block.id == last_block.id and block.hash == last_block.hash:
            return

        previous_hash = last_block.hash
        if block.id == last_block.id + 1 and self._block_validator.validate(
            block, previous_hash
        ):
            self._blockchain_repository.append_block(block)
            tx_ids = [tx.id for tx in block.transactions]
            self._transaction_repository.remove_from_mempool(tx_ids)
            await self._message_sender.broadcast(
                Message(
                    type=MessageType.NEW_BLOCK,
                    payload=NewBlockPayload(block=block_to_dto(block)),
                ),
                exclude_node_id=peer.node_id,
            )
            return

        if block.id >= local_height and block.last_hash != previous_hash:
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
        if len(blocks) <= self._blockchain_repository.get_height():
            return
        if await self._chain_dispatcher.verify(blocks):
            self._blockchain_repository.replace_chain(blocks)
            confirmed_ids = {
                tx.id for block in blocks for tx in block.transactions
            }
            self._transaction_repository.remove_from_mempool(list(confirmed_ids))

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
        for dto in message.payload.transactions:
            tx = transaction_from_dto(dto)
            if self._transaction_repository.exists_in_mempool_or_chain(tx.id):
                continue
            if self._transaction_validator.validate(tx):
                self._transaction_repository.add_to_mempool(tx)
