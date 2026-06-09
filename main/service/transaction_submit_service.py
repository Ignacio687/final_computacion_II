"""Implementación de ITransactionSubmit."""

from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.transaction_submit import ITransactionSubmit
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.domain.models.message import Message, MessageType
from main.domain.models.payloads import NewTxPayload
from main.domain.models.transaction import Transaction
from main.repository.dto.mappers import transaction_to_dto


class TransactionSubmitService(ITransactionSubmit):
    """Valida, persiste en mempool y propaga NEW_TX."""

    def __init__(
        self,
        transaction_repository: ITransactionRepository,
        transaction_validator: ITransactionValidator,
        message_sender: IMessageSender,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._transaction_validator = transaction_validator
        self._message_sender = message_sender

    async def submit_transaction(self, tx: Transaction) -> bool:
        if not self._transaction_validator.validate(tx):
            return False
        if self._transaction_repository.exists_in_mempool_or_chain(tx.id):
            return False
        self._transaction_repository.add_to_mempool(tx)
        message = Message(
            type=MessageType.NEW_TX,
            payload=NewTxPayload(transaction=transaction_to_dto(tx)),
        )
        await self._message_sender.broadcast(message)
        return True
