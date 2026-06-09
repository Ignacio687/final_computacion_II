"""Adaptador TCP: envío de mensajes a peers (sobre cifrado + firmado)."""

from typing import List

from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.signer import ISigner
from main.infrastructure.serialization.message_codec import MessageCodec
from main.domain.models.message import Message
from main.domain.models.node_info import NodeInfo


class TCPMessageSender(IMessageSender):
    """Implementación TCP de IMessageSender (ver doc/protocolo.md §6).

    Mantiene una conexión TCP persistente con cada peer. Al conectar realiza el handshake
    HELLO (§6.5). Ante caída de conexión reintenta con un delay fijo
    `reconnect_delay_seconds` (sin keepalive). Para cada Message: construye el sobre con
    `codec` (payload cifrado con la clave precompartida + firma del nodo con `signer`) y
    antepone 4 bytes big-endian con la longitud."""

    def __init__(
        self,
        peers: List[NodeInfo],
        signer: ISigner,
        codec: MessageCodec,
        node_id: str,
        listen_port: int,
        reconnect_delay_seconds: float,
    ) -> None:
        self._peers = peers
        self._signer = signer
        self._codec = codec
        self._node_id = node_id
        self._listen_port = listen_port
        self._reconnect_delay_seconds = reconnect_delay_seconds

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def send_to_peer(self, peer: NodeInfo, message: Message) -> None:
        raise NotImplementedError

    async def broadcast(self, message: Message, exclude_node_id: str | None = None) -> None:
        raise NotImplementedError

    def connected_count(self) -> int:
        raise NotImplementedError
