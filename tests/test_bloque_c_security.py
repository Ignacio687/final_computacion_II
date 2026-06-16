"""Tests de hardening Bloque C: cola verify y allowlist TCP."""

import asyncio
import struct
import threading
from unittest.mock import MagicMock

import pytest

from main.domain.models.message import Message, MessageType
from main.domain.models.node_info import NodeInfo
from main.domain.models.payloads import HelloPayload
from main.infrastructure.serialization.canonical import bytes_to_b64
from main.infrastructure.tcp.tcp_message_receiver import TCPMessageReceiver
from main.infrastructure.tcp.tcp_message_sender import TCPMessageSender
from main.infrastructure.validation.chain_verification_dispatcher import (
    ChainVerificationDispatcher,
)
from tests.node_test_helpers import free_port
from tests.test_block_chain_validation import _genesis_provider


@pytest.mark.asyncio
async def test_chain_dispatcher_rejects_when_queue_full():
    release = threading.Event()

    chain_verifier = MagicMock()

    def slow_verify(blocks):
        release.wait(timeout=5.0)
        return True

    chain_verifier.verify_chain.side_effect = slow_verify
    dispatcher = ChainVerificationDispatcher(chain_verifier, workers=1)
    dispatcher.start()
    try:
        genesis = _genesis_provider().get_genesis_block()
        first = asyncio.create_task(dispatcher.verify([genesis]))
        await asyncio.sleep(0.05)

        pending = [
            asyncio.create_task(dispatcher.verify([genesis])) for _ in range(32)
        ]
        await asyncio.sleep(0.05)

        rejected = await dispatcher.verify([genesis])
        assert rejected is False

        release.set()
        await first
        await asyncio.gather(*pending)
    finally:
        dispatcher.stop()


async def _send_framed_message(
    writer: asyncio.StreamWriter, codec, message: Message, sender_node_id: str
) -> None:
    raw = codec.encode(message, sender_node_id)
    writer.write(struct.pack(">I", len(raw)) + raw)
    await writer.drain()


async def _read_framed_message(reader: asyncio.StreamReader, codec, peer_public_key):
    length_bytes = await reader.readexactly(4)
    length = struct.unpack(">I", length_bytes)[0]
    raw = await reader.readexactly(length)
    return codec.decode(raw, peer_public_key)


@pytest.mark.asyncio
async def test_tcp_receiver_rejects_unlisted_hello(codec, signer):
    port = free_port()
    sender = TCPMessageSender(
        peers=[],
        signer=signer,
        codec=codec,
        node_id="node-a",
        listen_port=port,
        reconnect_delay_seconds=1.0,
    )
    allowed = [NodeInfo(host="127.0.0.1", port=9999, node_id="allowed-peer")]
    receiver = TCPMessageReceiver(
        "127.0.0.1",
        port,
        codec,
        "node-b",
        port,
        sender,
        signer.get_public_key(),
        allowed,
    )
    await receiver.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        hello = Message(
            type=MessageType.HELLO,
            payload=HelloPayload(
                node_id="intruder",
                public_key=bytes_to_b64(signer.get_public_key()),
                listen_port=8888,
            ),
        )
        await _send_framed_message(writer, codec, hello, "intruder")
        with pytest.raises(asyncio.IncompleteReadError):
            await _read_framed_message(reader, codec, signer.get_public_key())
    finally:
        await receiver.stop()


@pytest.mark.asyncio
async def test_tcp_receiver_accepts_docker_style_peer_name(codec, signer):
    port = free_port()
    client_listen = free_port()
    sender = TCPMessageSender(
        peers=[],
        signer=signer,
        codec=codec,
        node_id="node-a",
        listen_port=port,
        reconnect_delay_seconds=1.0,
    )
    allowed = [NodeInfo(host="client-node", port=client_listen)]
    receiver = TCPMessageReceiver(
        "127.0.0.1",
        port,
        codec,
        "node-b",
        port,
        sender,
        signer.get_public_key(),
        allowed,
    )
    await receiver.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        hello = Message(
            type=MessageType.HELLO,
            payload=HelloPayload(
                node_id="client-node",
                public_key=bytes_to_b64(signer.get_public_key()),
                listen_port=client_listen,
            ),
        )
        await _send_framed_message(writer, codec, hello, "client-node")
        response = await _read_framed_message(reader, codec, signer.get_public_key())
        assert response.type == MessageType.HELLO
        assert response.payload.node_id == "node-b"
    finally:
        await receiver.stop()


@pytest.mark.asyncio
async def test_tcp_receiver_accepts_listed_hello(codec, signer):
    port = free_port()
    client_listen = free_port()
    sender = TCPMessageSender(
        peers=[],
        signer=signer,
        codec=codec,
        node_id="node-a",
        listen_port=port,
        reconnect_delay_seconds=1.0,
    )
    allowed = [NodeInfo(host="127.0.0.1", port=client_listen, node_id="client-node")]
    receiver = TCPMessageReceiver(
        "127.0.0.1",
        port,
        codec,
        "node-b",
        port,
        sender,
        signer.get_public_key(),
        allowed,
    )
    await receiver.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        hello = Message(
            type=MessageType.HELLO,
            payload=HelloPayload(
                node_id="client-node",
                public_key=bytes_to_b64(signer.get_public_key()),
                listen_port=client_listen,
            ),
        )
        await _send_framed_message(writer, codec, hello, "client-node")
        response = await _read_framed_message(reader, codec, signer.get_public_key())
        assert response.type == MessageType.HELLO
        assert isinstance(response.payload, HelloPayload)
        assert response.payload.node_id == "node-b"
    finally:
        await receiver.stop()
