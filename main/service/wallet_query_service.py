"""Implementación de IWalletQuery. Solo lee de los repositorios; no modifica estado."""

from typing import Callable, List

from main.application.interfaces.wallet_query import IWalletQuery
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.domain.models.transaction import Transaction


class WalletQueryService(IWalletQuery):
    """Compone los datos para los handlers HTTP GET (balance, transacciones, estado)."""

    def __init__(
        self,
        transaction_repository: ITransactionRepository,
        blockchain_repository: IBlockchainRepository,
        node_id: str,
        difficulty: int,
        get_peers_connected: Callable[[], int],
    ) -> None:
        self._transaction_repository = transaction_repository
        self._blockchain_repository = blockchain_repository
        self._node_id = node_id
        self._difficulty = difficulty
        self._get_peers_connected = get_peers_connected

    def get_balance(self, address: str) -> int:
        raise NotImplementedError

    def get_transactions(self, address: str | None, limit: int) -> List[Transaction]:
        raise NotImplementedError

    def get_status(self) -> dict:
        raise NotImplementedError
