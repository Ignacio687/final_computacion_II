"""Interfaz: persistencia y lectura de transacciones (mempool y confirmadas)."""

from abc import ABC, abstractmethod
from typing import List

from main.domain.models.transaction import Transaction


class ITransactionRepository(ABC):
    """Contrato para consultas a nivel de TRANSACCIÓN.

    Frontera de responsabilidad con IBlockchainRepository:
    - IBlockchainRepository es dueño de la estructura de la CADENA (bloques, encadenado,
      altura, append/replace). Es la fuente de verdad de lo confirmado.
    - ITransactionRepository es dueño del MEMPOOL (pendientes) y de las CONSULTAS por
      transacción/dirección sobre lo confirmado (balance, historial). Las lecturas
      confirmadas se resuelven sobre la misma BD SQLite (tabla de tx indexada por bloque
      que `append_block`/`replace_chain` mantienen), pero NUNCA modifica la cadena.
    """

    @abstractmethod
    def add_to_mempool(self, tx: Transaction) -> None:
        """Añade la transacción al mempool y la persiste. No valida; la validación es responsabilidad
        de ITransactionValidator antes de llamar a este método."""
        ...

    @abstractmethod
    def get_mempool(self) -> List[Transaction]:
        """Devuelve todas las transacciones pendientes del mempool, en orden de inserción ascendente."""
        ...

    @abstractmethod
    def remove_from_mempool(self, tx_ids: List[str]) -> None:
        """Elimina del mempool las transacciones cuyos id estén en la lista
        (al confirmarse en un bloque que se añade a la cadena)."""
        ...

    @abstractmethod
    def exists_in_mempool_or_chain(self, tx_id: str) -> bool:
        """Devuelve True si la transacción ya está en mempool o confirmada en la cadena."""
        ...

    @abstractmethod
    def get_balance(self, address: str) -> int:
        """Balance de la dirección calculado SOLO sobre la cadena confirmada (no incluye mempool).
        Suma recompensas de minado recibidas, suma transacciones recibidas, resta transacciones enviadas."""
        ...

    @abstractmethod
    def get_transactions_for_address(self, address: str, limit: int) -> List[Transaction]:
        """Últimas `limit` transacciones de la cadena confirmada que tengan `address` como
        sender o receiver, en orden cronológico descendente (más reciente primero)."""
        ...

    @abstractmethod
    def get_recent_transactions(self, limit: int) -> List[Transaction]:
        """Últimas `limit` transacciones de la cadena confirmada (cualquier dirección),
        en orden cronológico descendente."""
        ...

    @abstractmethod
    def get_total_supply(self) -> int:
        """Moneda en circulación confirmada (emisión génesis + coinbase, sin doble conteo)."""
        ...
