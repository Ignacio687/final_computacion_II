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
from main.infrastructure.logging.node_logger import get_logger, trunc
from main.infrastructure.validation.block_validator import (
    DefaultBlockValidator,
    balances_from_chain,
)
from main.infrastructure.validation.chain_verification_dispatcher import (
    ChainVerificationDispatcher,
)
from main.repository.dto.mappers import block_from_dto, block_to_dto, transaction_from_dto, transaction_to_dto

logger = get_logger("propagation")


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
                logger.debug(
                    "propagation: tx duplicada ignorada tx_id=%s de peer %s",
                    trunc(tx.id),
                    peer.node_id,
                )
                return
            if not self._transaction_validator.validate(tx):
                logger.info(
                    "propagation: tx rechazada tx_id=%s de peer %s",
                    trunc(tx.id),
                    peer.node_id,
                )
                return
            self._transaction_repository.add_to_mempool(tx)
        logger.info(
            "propagation: tx aceptada en mempool tx_id=%s de peer %s",
            trunc(tx.id),
            peer.node_id,
        )
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
                logger.debug(
                    "propagation: bloque antiguo ignorado block_id=%s de peer %s",
                    block.id,
                    peer.node_id,
                )
                return
            last_block = self._blockchain_repository.get_last_block()
            if last_block is None:
                return
            if block.id == last_block.id and block.hash == last_block.hash:
                logger.debug(
                    "propagation: bloque ya conocido block_id=%s de peer %s",
                    block.id,
                    peer.node_id,
                )
                return
            if block.id == local_height and block.hash != last_block.hash:
                needs_chain_sync = True
                logger.warning(
                    "propagation: fork detectado en altura %s, solicitando cadena a %s",
                    local_height,
                    peer.node_id,
                )
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
                    logger.warning(
                        "propagation: bloque rechazado al persistir block_id=%s hash=%s",
                        block.id,
                        trunc(block.hash),
                    )
                else:
                    tx_ids = [tx.id for tx in block.transactions]
                    self._transaction_repository.remove_from_mempool(tx_ids)
                    logger.info(
                        "propagation: bloque appendido block_id=%s hash=%s de peer %s",
                        block.id,
                        trunc(block.hash),
                        peer.node_id,
                    )
            elif block.id >= local_height and block.last_hash != previous_hash:
                needs_chain_sync = True
                logger.warning(
                    "propagation: cadena desincronizada, solicitando sync a %s",
                    peer.node_id,
                )
            else:
                logger.info(
                    "propagation: bloque rechazado block_id=%s de peer %s",
                    block.id,
                    peer.node_id,
                )
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
        since_height = message.payload.since_height
        blocks = self._blockchain_repository.get_chain_since(since_height)
        logger.info(
            "propagation: respondiendo CHAIN_RESPONSE a %s since_height=%s blocks=%d",
            peer.node_id,
            since_height,
            len(blocks),
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
            logger.debug(
                "propagation: CHAIN_RESPONSE sin cadena más larga (local=%s)",
                local_height,
            )
            return
        if not await self._chain_dispatcher.verify(blocks):
            logger.warning(
                "propagation: CHAIN_RESPONSE rechazada (verificación fallida) "
                "blocks=%d tip=%s",
                len(blocks),
                blocks[-1].id,
            )
            return
        async with self._chain_lock:
            local_height = self._blockchain_repository.get_height()
            if not blocks or blocks[-1].id <= local_height:
                return
            old_height = local_height
            self._blockchain_repository.replace_chain(
                blocks,
                tx_reinsert_filter=self._transaction_validator.validate,
            )
            new_height = self._blockchain_repository.get_height()
            logger.info(
                "propagation: replace_chain altura %s -> %s (%d bloques)",
                old_height,
                new_height,
                len(blocks),
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
        logger.info(
            "propagation: respondiendo MEMPOOL_RESPONSE a %s txs=%d",
            peer.node_id,
            len(mempool),
        )
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
            added = 0
            for dto in message.payload.transactions:
                tx = transaction_from_dto(dto)
                if self._transaction_repository.exists_in_mempool_or_chain(tx.id):
                    continue
                if self._transaction_validator.validate(tx):
                    self._transaction_repository.add_to_mempool(tx)
                    added += 1
            if added:
                logger.info(
                    "propagation: %d tx(s) añadidas desde MEMPOOL_RESPONSE",
                    added,
                )
