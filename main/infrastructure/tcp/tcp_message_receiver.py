"""Adaptador TCP: servidor que recibe mensajes y los entrega al handler registrado."""

from main.application.interfaces.message_receiver import IMessageReceiver, MessageHandler
from main.infrastructure.serialization.message_codec import MessageCodec


class TCPMessageReceiver(IMessageReceiver):
    """Implementación TCP de IMessageReceiver (ver doc/protocolo.md §6).

    Levanta `asyncio.start_server` en `bind_host:port`. Por cada conexión entrante:
    lee 4 bytes (big-endian) con la longitud del sobre, lee el cuerpo y lo decodifica con
    `codec` (descifra el payload + verifica la firma contra la clave pública del peer
    obtenida en el handshake HELLO). El primer mensaje de una conexión debe ser HELLO;
    hasta registrarlo no se entregan otros mensajes. Los mensajes válidos (no-HELLO) se
    pasan al handler registrado."""

    def __init__(self, bind_host: str, port: int, codec: MessageCodec) -> None:
        self._bind_host = bind_host
        self._port = port
        self._codec = codec
        self._handler: MessageHandler | None = None

    def set_handler(self, handler: MessageHandler) -> None:
        raise NotImplementedError

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError
