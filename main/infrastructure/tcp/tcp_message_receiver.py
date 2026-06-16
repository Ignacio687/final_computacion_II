"""Adaptador TCP: servidor que recibe mensajes y los entrega al handler registrado."""

import asyncio
import struct
from typing import List, Optional

from main.application.interfaces.message_receiver import IMessageReceiver, MessageHandler
from main.domain.models.message import Message, MessageType
from main.domain.models.node_info import NodeInfo
from main.domain.models.payloads import HelloPayload
from main.infrastructure.logging.node_logger import get_logger, message_detail
from main.infrastructure.serialization.canonical import b64_to_bytes, bytes_to_b64
from main.infrastructure.serialization.message_codec import MessageCodec
from main.infrastructure.tcp.frame_limits import MAX_FRAME_BYTES
from main.infrastructure.tcp.tcp_message_sender import TCPMessageSender

logger = get_logger("tcp")


class TCPMessageReceiver(IMessageReceiver):
    """Implementación TCP de IMessageReceiver (ver doc/protocolo.md §6)."""

    def __init__(
        self,
        bind_host: str,
        port: int,
        codec: MessageCodec,
        node_id: str,
        listen_port: int,
        message_sender: TCPMessageSender,
        public_key_der: bytes,
        allowed_peers: List[NodeInfo],
    ) -> None:
        self._bind_host = bind_host
        self._port = port
        self._codec = codec
        self._node_id = node_id
        self._listen_port = listen_port
        self._message_sender = message_sender
        self._public_key_b64 = bytes_to_b64(public_key_der)
        self._allowed_peers = allowed_peers
        self._handler: MessageHandler | None = None
        self._server: Optional[asyncio.Server] = None

    def _is_peer_allowed(
        self, remote_host: str, remote_port: int, hello: HelloPayload
    ) -> bool:
        for peer in self._allowed_peers:
            if peer.node_id is not None and peer.node_id == hello.node_id:
                return True
            if peer.host == remote_host and peer.port in (remote_port, hello.listen_port):
                return True
        return False

    def set_handler(self, handler: MessageHandler) -> None:
        self._handler = handler

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            self._bind_host,
            self._port,
        )
        logger.info("tcp: escuchando en %s:%s", self._bind_host, self._port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer_host, peer_port = writer.get_extra_info("peername")[:2]
        logger.info("tcp: conexión entrante desde %s:%s", peer_host, peer_port)
        handshake_done = False
        peer_node_id: Optional[str] = None
        peer_public_key: Optional[bytes] = None
        lock = asyncio.Lock()

        try:
            while True:
                length_bytes = await reader.readexactly(4)
                length = struct.unpack(">I", length_bytes)[0]
                if length > MAX_FRAME_BYTES:
                    raise ValueError(
                        f"trama TCP excede MAX_FRAME_BYTES ({MAX_FRAME_BYTES})"
                    )
                raw = await reader.readexactly(length)
                message = self._codec.decode(
                    raw,
                    peer_public_key if handshake_done else None,
                    expected_sender_node_id=peer_node_id if handshake_done else None,
                )

                if message.type == MessageType.HELLO:
                    hello = message.payload
                    if not isinstance(hello, HelloPayload):
                        logger.warning(
                            "tcp: HELLO inválido desde %s:%s",
                            peer_host,
                            peer_port,
                        )
                        break
                    if not self._is_peer_allowed(peer_host, peer_port, hello):
                        logger.warning(
                            "tcp: peer no autorizado %s:%s node_id=%s",
                            peer_host,
                            peer_port,
                            hello.node_id,
                        )
                        break
                    peer_node_id = hello.node_id
                    peer_public_key = b64_to_bytes(hello.public_key)
                    handshake_done = True
                    logger.info(
                        "tcp: handshake entrante OK peer=%s:%s node_id=%s",
                        peer_host,
                        peer_port,
                        peer_node_id,
                    )
                    await self._message_sender.register_incoming(
                        peer_node_id,
                        peer_host,
                        peer_port,
                        reader,
                        writer,
                        peer_public_key,
                    )
                    response = Message(
                        type=MessageType.HELLO,
                        payload=HelloPayload(
                            node_id=self._node_id,
                            public_key=self._public_key_b64,
                            listen_port=self._listen_port,
                        ),
                    )
                    await self._write_message(writer, lock, response)
                    continue

                if not handshake_done:
                    logger.warning(
                        "tcp: mensaje %s antes del handshake desde %s:%s",
                        message.type.value,
                        peer_host,
                        peer_port,
                    )
                    break

                if peer_node_id is not None:
                    logger.info(
                        "tcp: <- peer %s %s",
                        peer_node_id,
                        message_detail(message),
                    )
                if self._handler is not None and peer_node_id is not None:
                    peer = NodeInfo(
                        host=peer_host,
                        port=peer_port,
                        node_id=peer_node_id,
                    )
                    try:
                        await self._handler(peer, message)
                    except Exception:
                        logger.warning(
                            "tcp: error al procesar %s de peer %s",
                            message.type.value,
                            peer_node_id,
                            exc_info=True,
                        )
        except (asyncio.IncompleteReadError, ConnectionResetError, ValueError) as exc:
            logger.debug(
                "tcp: conexión entrante cerrada %s:%s: %s",
                peer_host,
                peer_port,
                exc,
            )
        finally:
            if peer_node_id is not None:
                self._message_sender.unregister_incoming(peer_node_id, writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _write_message(
        self,
        writer: asyncio.StreamWriter,
        lock: asyncio.Lock,
        message: Message,
    ) -> None:
        raw = self._codec.encode(message, self._node_id)
        framed = struct.pack(">I", len(raw)) + raw
        async with lock:
            writer.write(framed)
            await writer.drain()
