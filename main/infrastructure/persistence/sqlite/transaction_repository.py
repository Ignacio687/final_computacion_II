"""Adaptador: persistencia de transacciones (mempool y confirmadas) en SQLite."""

from typing import List

from main.application.interfaces.transaction_repository import ITransactionRepository
from main.domain.models.transaction import Transaction


class SQLiteTransactionRepository(ITransactionRepository):
    """Implementación de ITransactionRepository usando SQLite (esquema canónico en
    doc/protocolo.md §11: tablas `mempool` y `transactions`). db_path es el mismo archivo
    que usa SQLiteBlockchainRepository. Las consultas de balance/historial se calculan solo
    sobre `transactions` (confirmadas), nunca sobre `mempool`."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def add_to_mempool(self, tx: Transaction) -> None:
        raise NotImplementedError

    def get_mempool(self) -> List[Transaction]:
        raise NotImplementedError

    def remove_from_mempool(self, tx_ids: List[str]) -> None:
        raise NotImplementedError

    def exists_in_mempool_or_chain(self, tx_id: str) -> bool:
        raise NotImplementedError

    def get_balance(self, address: str) -> int:
        raise NotImplementedError

    def get_transactions_for_address(self, address: str, limit: int) -> List[Transaction]:
        raise NotImplementedError

    def get_recent_transactions(self, limit: int) -> List[Transaction]:
        raise NotImplementedError
