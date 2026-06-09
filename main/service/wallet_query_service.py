"""Implementación de IWalletQuery. Solo lee de los repositorios; no modifica estado."""

from typing import List

from main.application.interfaces.wallet_query import IWalletQuery
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.message_sender import IMessageSender
from main.domain.models.transaction import Transaction


class WalletQueryService(IWalletQuery):
    """Compone los datos para los handlers HTTP GET (balance, transacciones, estado).

    Recibe `message_sender` (no un callable suelto) para exponer `peers_connected` en
    GET /status vía `message_sender.connected_count()`, respetando la inversión de
    dependencias (depende de la interfaz IMessageSender)."""

    def __init__(
        self,
        transaction_repository: ITransactionRepository,
        blockchain_repository: IBlockchainRepository,
        message_sender: IMessageSender,
        node_id: str,
        difficulty: int,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._blockchain_repository = blockchain_repository
        self._message_sender = message_sender
        self._node_id = node_id
        self._difficulty = difficulty

    def get_balance(self, address: str) -> int:
        raise NotImplementedError

    def get_transactions(self, address: str | None, limit: int) -> List[Transaction]:
        raise NotImplementedError

    def get_status(self) -> dict:
        raise NotImplementedError
