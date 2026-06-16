"""Implementación de ITransactionSubmit."""

import asyncio

from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.transaction_submit import ITransactionSubmit
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.domain.models.message import Message, MessageType
from main.domain.models.payloads import NewTxPayload
from main.domain.models.transaction import Transaction
from main.infrastructure.logging.node_logger import get_logger, trunc
from main.repository.dto.mappers import transaction_to_dto

logger = get_logger("tx")


class TransactionSubmitService(ITransactionSubmit):
    def __init__(
        self,
        transaction_repository: ITransactionRepository,
        transaction_validator: ITransactionValidator,
        message_sender: IMessageSender,
        chain_lock: asyncio.Lock,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._transaction_validator = transaction_validator
        self._message_sender = message_sender
        self._chain_lock = chain_lock

    async def submit_transaction(self, tx: Transaction) -> bool:
        async with self._chain_lock:
            if not self._transaction_validator.validate(tx):
                logger.info("tx: rechazada tx_id=%s (validación)", trunc(tx.id))
                return False
            if self._transaction_repository.exists_in_mempool_or_chain(tx.id):
                logger.info("tx: rechazada tx_id=%s (duplicada)", trunc(tx.id))
                return False
            self._transaction_repository.add_to_mempool(tx)
        logger.info("tx: aceptada en mempool tx_id=%s", trunc(tx.id))
        message = Message(
            type=MessageType.NEW_TX,
            payload=NewTxPayload(transaction=transaction_to_dto(tx)),
        )
        await self._message_sender.broadcast(message)
        return True
