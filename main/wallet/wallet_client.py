"""Cliente HTTP de la billetera hacia un nodo HashCoin."""

from typing import List

from main.domain.models.transaction import Transaction


class WalletClient:
    """Cliente HTTP usado por la consola de la billetera y por el generador de tx de prueba.

    Endpoints consumidos del nodo:
        GET  /balance?address=<addr>
        GET  /transactions?address=<addr|optional>&limit=<n>
        GET  /status
        POST /tx   (cuerpo JSON con la TransactionDTO firmada)

    `node_url` es la URL base (http://host:port), sin slash final.
    """

    def __init__(self, node_url: str) -> None:
        self._node_url = node_url

    def get_balance(self, address: str) -> int:
        raise NotImplementedError

    def get_transactions(self, address: str | None, limit: int) -> List[Transaction]:
        raise NotImplementedError

    def get_status(self) -> dict:
        raise NotImplementedError

    def submit_transaction(self, tx: Transaction) -> bool:
        """Devuelve True si el nodo aceptó la transacción (HTTP 200/201), False en caso contrario."""
        raise NotImplementedError
