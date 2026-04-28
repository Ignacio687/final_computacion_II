"""Adaptador TCP: envío de mensajes a peers (JSON cifrado/firmado)."""

from typing import List

from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.signer import ISigner
from main.domain.models.message import Message
from main.domain.models.node_info import NodeInfo


class TCPMessageSender(IMessageSender):
    """Implementación TCP de IMessageSender.

    Mantiene una conexión TCP persistente con cada peer; reconecta con backoff exponencial
    desde `reconnect_initial_seconds` hasta `reconnect_max_seconds`. Serializa cada Message
    a JSON, firma el payload con `signer` y antepone 4 bytes (big-endian) con la longitud
    del cuerpo."""

    def __init__(
        self,
        peers: List[NodeInfo],
        signer: ISigner,
        reconnect_initial_seconds: float,
        reconnect_max_seconds: float,
    ) -> None:
        self._peers = peers
        self._signer = signer
        self._reconnect_initial_seconds = reconnect_initial_seconds
        self._reconnect_max_seconds = reconnect_max_seconds

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def send_to_peer(self, peer: NodeInfo, message: Message) -> None:
        raise NotImplementedError

    async def broadcast(self, message: Message) -> None:
        raise NotImplementedError
