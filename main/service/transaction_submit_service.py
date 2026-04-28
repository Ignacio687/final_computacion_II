"""Implementación de ITransactionSubmit: validar, añadir a mempool y propagar NEW_TX."""

from main.application.interfaces.transaction_submit import ITransactionSubmit
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.application.interfaces.message_sender import IMessageSender
from main.domain.models.transaction import Transaction


class TransactionSubmitService(ITransactionSubmit):
    """Flujo:
    1. Validar con ITransactionValidator. Si falla -> False.
    2. Si exists_in_mempool_or_chain -> False.
    3. add_to_mempool.
    4. broadcast NEW_TX a todos los peers.
    5. Devolver True.
    """

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
        raise NotImplementedError
