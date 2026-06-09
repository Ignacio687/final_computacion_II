"""Adaptador HTTP: servidor del nodo (GET /balance, GET /transactions, GET /status, POST /tx)."""

from main.controller.http_handlers import HTTPHandlers


class HTTPServer:
    """Servidor HTTP del nodo. Bindea en `bind_host:port`. Enruta cada request al método
    correspondiente de `HTTPHandlers` y devuelve JSON en todas las respuestas
    (ver formato en doc/protocolo.md §10)."""

    def __init__(self, bind_host: str, port: int, handlers: HTTPHandlers) -> None:
        self._bind_host = bind_host
        self._port = port
        self._handlers = handlers

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError
