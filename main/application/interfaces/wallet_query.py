"""Interfaz: consultas que expone el nodo para clientes HTTP (billetera)."""

from abc import ABC, abstractmethod
from typing import List

from main.domain.models.transaction import Transaction


class IWalletQuery(ABC):
    """Contrato consumido por los handlers HTTP GET."""

    @abstractmethod
    def get_balance(self, address: str) -> int:
        """Balance de la dirección calculado sobre la cadena confirmada (no incluye mempool)."""
        ...

    @abstractmethod
    def get_transactions(self, address: str | None, limit: int) -> List[Transaction]:
        """Si `address` no es None: últimas `limit` transacciones confirmadas que involucren
        a esa dirección como sender o receiver. Si `address` es None: últimas `limit`
        transacciones confirmadas (cualquier dirección). Orden cronológico descendente."""
        ...

    @abstractmethod
    def get_status(self) -> dict:
        """Estado del nodo. Estructura exacta:
        {
          "node_id": str,
          "height": int,
          "difficulty": int,
          "mempool_size": int,
          "peers_connected": int
        }"""
        ...
