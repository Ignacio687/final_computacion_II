"""Adaptador HTTP: servidor del nodo (GET /balance, GET /transactions, GET /status, POST /tx)."""

from main.application.interfaces.wallet_query import IWalletQuery
from main.application.interfaces.transaction_submit import ITransactionSubmit


class HTTPServer:
    """Servidor HTTP del nodo. Bindea en `bind_host:port`. Delega en IWalletQuery (consultas)
    y en ITransactionSubmit (envío de tx). Devuelve JSON en todas las respuestas."""

    def __init__(
        self,
        bind_host: str,
        port: int,
        wallet_query: IWalletQuery,
        transaction_submit: ITransactionSubmit,
    ) -> None:
        self._bind_host = bind_host
        self._port = port
        self._wallet_query = wallet_query
        self._transaction_submit = transaction_submit

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError
