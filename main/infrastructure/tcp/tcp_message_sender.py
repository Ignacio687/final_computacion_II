"""Adaptador TCP: envío de mensajes a peers (sobre cifrado + firmado)."""

import asyncio
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from main.application.interfaces.message_receiver import MessageHandler
from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.signer import ISigner
from main.domain.models.message import Message, MessageType
from main.domain.models.node_info import NodeInfo
from main.domain.models.payloads import HelloPayload
from main.infrastructure.serialization.canonical import bytes_to_b64
from main.infrastructure.serialization.message_codec import MessageCodec


def _peer_key(host: str, port: int) -> str:
    return f"{host}:{port}"


@dataclass
class _PeerConnection:
    host: str
    port: int
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    node_id: Optional[str] = None
    public_key: Optional[bytes] = None
    handshake_done: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class TCPMessageSender(IMessageSender):
    """Implementación TCP de IMessageSender (ver doc/protocolo.md §6)."""

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
        self._outgoing: Dict[str, _PeerConnection] = {}
        self._incoming: Dict[str, _PeerConnection] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._handler: MessageHandler | None = None

    def set_handler(self, handler: MessageHandler) -> None:
        self._handler = handler

    def register_incoming(
        self,
        node_id: str,
        host: str,
        port: int,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        public_key: bytes,
    ) -> None:
        for key, conn in list(self._outgoing.items()):
            if conn.node_id == node_id:
                self._outgoing.pop(key, None)
                try:
                    asyncio.get_running_loop().create_task(self._close_connection(conn))
                except RuntimeError:
                    pass

        conn = _PeerConnection(
            host=host,
            port=port,
            reader=reader,
            writer=writer,
            node_id=node_id,
            public_key=public_key,
            handshake_done=True,
        )
        self._incoming[node_id] = conn

    def unregister_incoming(
        self, node_id: str, writer: asyncio.StreamWriter
    ) -> None:
        conn = self._incoming.get(node_id)
        if conn is not None and conn.writer is writer:
            self._incoming.pop(node_id, None)

    async def start(self) -> None:
        self._running = True
        for peer in self._peers:
            task = asyncio.create_task(self._maintain_connection(peer))
            self._tasks.append(task)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        for conn in list(self._outgoing.values()):
            await self._close_connection(conn)
        self._outgoing.clear()
        for conn in list(self._incoming.values()):
            await self._close_connection(conn)
        self._incoming.clear()

    async def send_to_peer(self, peer: NodeInfo, message: Message) -> None:
        conn = self._resolve_connection(peer)
        if conn is None or not conn.handshake_done:
            return
        await self._write_message(conn, message)

    async def broadcast(
        self, message: Message, exclude_node_id: str | None = None
    ) -> None:
        targets: List[_PeerConnection] = []
        seen: set[str] = set()
        for conn in self._outgoing.values():
            if not conn.handshake_done or not conn.node_id:
                continue
            if conn.node_id == exclude_node_id or conn.node_id in seen:
                continue
            seen.add(conn.node_id)
            targets.append(conn)
        for conn in self._incoming.values():
            if not conn.handshake_done or not conn.node_id:
                continue
            if conn.node_id == exclude_node_id or conn.node_id in seen:
                continue
            seen.add(conn.node_id)
            targets.append(conn)
        await asyncio.gather(
            *(self._write_message(conn, message) for conn in targets),
            return_exceptions=True,
        )

    def connected_count(self) -> int:
        seen: set[str] = set()
        count = 0
        for conn in self._outgoing.values():
            if conn.handshake_done and conn.node_id and conn.node_id not in seen:
                seen.add(conn.node_id)
                count += 1
        for conn in self._incoming.values():
            if conn.handshake_done and conn.node_id and conn.node_id not in seen:
                seen.add(conn.node_id)
                count += 1
        return count

    def _resolve_connection(self, peer: NodeInfo) -> Optional[_PeerConnection]:
        if peer.node_id and peer.node_id in self._incoming:
            return self._incoming[peer.node_id]
        key = _peer_key(peer.host, peer.port)
        if key in self._outgoing:
            return self._outgoing[key]
        if peer.node_id:
            for conn in self._outgoing.values():
                if conn.node_id == peer.node_id:
                    return conn
            for conn in self._incoming.values():
                if conn.node_id == peer.node_id:
                    return conn
        return None

    async def _maintain_connection(self, peer: NodeInfo) -> None:
        key = _peer_key(peer.host, peer.port)
        while self._running:
            conn: Optional[_PeerConnection] = None
            try:
                reader, writer = await asyncio.open_connection(peer.host, peer.port)
                conn = _PeerConnection(
                    host=peer.host,
                    port=peer.port,
                    reader=reader,
                    writer=writer,
                )
                self._outgoing[key] = conn
                await self._perform_handshake_as_initiator(conn)
                await self._read_loop(conn)
            except asyncio.CancelledError:
                break
            except Exception:
                if conn is not None:
                    await self._close_connection(conn)
                    self._outgoing.pop(key, None)
                if self._running:
                    await asyncio.sleep(self._reconnect_delay_seconds)
            else:
                if conn is not None:
                    await self._close_connection(conn)
                    self._outgoing.pop(key, None)
                if self._running:
                    await asyncio.sleep(self._reconnect_delay_seconds)

    async def _perform_handshake_as_initiator(self, conn: _PeerConnection) -> None:
        await self._write_message(
            conn,
            Message(
                type=MessageType.HELLO,
                payload=HelloPayload(
                    node_id=self._node_id,
                    public_key=bytes_to_b64(self._signer.get_public_key()),
                    listen_port=self._listen_port,
                ),
            ),
            for_handshake=True,
        )
        message = await self._read_message(conn, peer_public_key=None)
        if message.type != MessageType.HELLO:
            raise ValueError("Se esperaba HELLO en el handshake saliente")
        hello = message.payload
        if not isinstance(hello, HelloPayload):
            raise ValueError("Payload HELLO inválido")
        from main.infrastructure.serialization.canonical import b64_to_bytes

        conn.node_id = hello.node_id
        conn.public_key = b64_to_bytes(hello.public_key)
        conn.handshake_done = True

    async def _read_loop(self, conn: _PeerConnection) -> None:
        while self._running and conn.handshake_done:
            try:
                message = await self._read_message(conn, conn.public_key)
            except (asyncio.IncompleteReadError, ConnectionResetError, ValueError):
                break
            if message.type == MessageType.HELLO:
                continue
            if self._handler is not None and conn.node_id is not None:
                peer = NodeInfo(host=conn.host, port=conn.port, node_id=conn.node_id)
                try:
                    await self._handler(peer, message)
                except Exception:
                    pass

    async def _write_message(
        self,
        conn: _PeerConnection,
        message: Message,
        *,
        for_handshake: bool = False,
    ) -> None:
        raw = self._codec.encode(message, self._node_id)
        framed = struct.pack(">I", len(raw)) + raw
        async with conn.lock:
            conn.writer.write(framed)
            await conn.writer.drain()

    async def _read_message(
        self, conn: _PeerConnection, peer_public_key: bytes | None
    ) -> Message:
        length_bytes = await conn.reader.readexactly(4)
        length = struct.unpack(">I", length_bytes)[0]
        raw = await conn.reader.readexactly(length)
        return self._codec.decode(raw, peer_public_key)

    async def _close_connection(self, conn: _PeerConnection) -> None:
        try:
            conn.writer.close()
            await conn.writer.wait_closed()
        except Exception:
            pass
