"""Interfaz: consultas que expone el nodo para clientes HTTP (billetera)."""

from abc import ABC, abstractmethod
from typing import List

from main.domain.models.active_account import ActiveAccount
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
        """Estado del nodo. Incluye node_id, height, difficulty, mempool_size,
        peers_connected y total_supply."""
        ...

    @abstractmethod
    def get_active_accounts(self, limit: int) -> List[ActiveAccount]:
        """Cuentas ordenadas por última modificación de saldo en la cadena confirmada."""
        ...
