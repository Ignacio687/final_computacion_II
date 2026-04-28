"""Adaptador TCP: servidor que recibe mensajes y los entrega al handler registrado."""

from main.application.interfaces.message_receiver import IMessageReceiver, MessageHandler
from main.application.interfaces.verifier import IVerifier


class TCPMessageReceiver(IMessageReceiver):
    """Implementación TCP de IMessageReceiver.

    Levanta `asyncio.start_server` en `bind_host:port`. Por cada conexión entrante:
    lee 4 bytes (big-endian) con la longitud del mensaje, lee el cuerpo, verifica la
    firma con `verifier`, deserializa a Message y llama al handler registrado."""

    def __init__(self, bind_host: str, port: int, verifier: IVerifier) -> None:
        self._bind_host = bind_host
        self._port = port
        self._verifier = verifier
        self._handler: MessageHandler | None = None

    def set_handler(self, handler: MessageHandler) -> None:
        raise NotImplementedError

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError
