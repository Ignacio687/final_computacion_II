"""Interfaz: aceptación de una transacción recibida desde el exterior (HTTP POST /tx)."""

from abc import ABC, abstractmethod

from main.domain.models.transaction import Transaction


class ITransactionSubmit(ABC):
    """Contrato consumido por el handler HTTP POST /tx."""

    @abstractmethod
    async def submit_transaction(self, tx: Transaction) -> bool:
        """Valida la transacción, la añade al mempool y la propaga por TCP a los peers.
        Devuelve True si fue aceptada y propagada; False si fue rechazada por validación
        o por estar duplicada."""
        ...
