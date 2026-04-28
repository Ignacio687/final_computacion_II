"""Handlers HTTP: GET /balance, GET /transactions, GET /status, POST /tx. Delegan en IWalletQuery e ITransactionSubmit."""

from main.application.interfaces.wallet_query import IWalletQuery
from main.application.interfaces.transaction_submit import ITransactionSubmit


class HTTPHandlers:
    """Mapeo ruta -> handler. Recibe request, extrae params/body, llama al puerto y devuelve response."""

    def __init__(self, wallet_query: IWalletQuery, transaction_submit: ITransactionSubmit) -> None:
        self._wallet_query = wallet_query
        self._transaction_submit = transaction_submit

    async def handle_get_balance(self, address: str) -> dict:
        raise NotImplementedError

    async def handle_get_transactions(self, address: str | None, limit: int) -> list:
        raise NotImplementedError

    async def handle_get_status(self) -> dict:
        raise NotImplementedError

    async def handle_post_tx(self, body: bytes) -> tuple[int, dict]:
        """Devuelve (status_code, body_dict)."""
        raise NotImplementedError
