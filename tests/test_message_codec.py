"""Tests 1.8: codec de mensajes TCP (doc/protocolo.md §6)."""

import json

import pytest

from main.domain.models.message import Message, MessageType
from main.domain.models.payloads import (
    ChainResponsePayload,
    GetChainPayload,
    GetMempoolPayload,
    HelloPayload,
    MempoolResponsePayload,
    NewBlockPayload,
    NewTxPayload,
)
from main.infrastructure.serialization.canonical import bytes_to_b64
from main.infrastructure.serialization.message_codec import MessageCodec
from main.repository.dto.block_dto import BlockDTO
from main.repository.dto.transaction_dto import TransactionDTO


def _sample_transaction() -> TransactionDTO:
    return TransactionDTO(
        id="tx-1",
        sender_id="a" * 64,
        receiver_id="b" * 64,
        amount=10,
        signature=bytes_to_b64(b"\xaa\xbb"),
        public_key=bytes_to_b64(b"\xcc\xdd"),
    )


def _sample_block() -> BlockDTO:
    return BlockDTO(
        id=1,
        last_hash="0" * 64,
        hash="1" * 64,
        timestamp=1700000000.0,
        target=1,
        nonce=3,
        transactions=[_sample_transaction()],
    )


def _messages_for_round_trip(codec: MessageCodec) -> list[Message]:
    node_public_key_b64 = bytes_to_b64(codec._signer.get_public_key())
    return [
        Message(
            type=MessageType.HELLO,
            payload=HelloPayload(
                node_id="node-1",
                public_key=node_public_key_b64,
                listen_port=9000,
            ),
        ),
        Message(
            type=MessageType.NEW_TX,
            payload=NewTxPayload(transaction=_sample_transaction()),
        ),
        Message(
            type=MessageType.NEW_BLOCK,
            payload=NewBlockPayload(block=_sample_block()),
        ),
        Message(
            type=MessageType.GET_CHAIN,
            payload=GetChainPayload(since_height=0),
        ),
        Message(
            type=MessageType.CHAIN_RESPONSE,
            payload=ChainResponsePayload(blocks=[_sample_block()]),
        ),
        Message(type=MessageType.GET_MEMPOOL, payload=GetMempoolPayload()),
        Message(
            type=MessageType.MEMPOOL_RESPONSE,
            payload=MempoolResponsePayload(transactions=[_sample_transaction()]),
        ),
    ]


@pytest.mark.parametrize("message_index", range(7))
def test_encode_decode_round_trip_per_type(codec: MessageCodec, message_index: int):
    message = _messages_for_round_trip(codec)[message_index]
    peer_public_key = codec._signer.get_public_key()
    raw = codec.encode(message, sender_node_id="node-local")
    if message.type == MessageType.HELLO:
        decoded = codec.decode(raw, peer_public_key=None)
    else:
        decoded = codec.decode(raw, peer_public_key=peer_public_key)
    assert decoded.type == message.type
    assert decoded.payload == message.payload


def test_message_codec_rejects_tampered_cipher(codec: MessageCodec, signer):
    message = Message(
        type=MessageType.GET_CHAIN,
        payload=GetChainPayload(since_height=0),
    )
    raw = bytearray(codec.encode(message, sender_node_id="node-local"))
    envelope = json.loads(bytes(raw).decode("utf-8"))
    cipher = bytearray(envelope["payload_cipher"].encode("ascii"))
    cipher[20] ^= 0x01
    envelope["payload_cipher"] = bytes(cipher).decode("ascii")
    tampered = json.dumps(envelope).encode("utf-8")
    with pytest.raises(Exception):
        codec.decode(tampered, peer_public_key=signer.get_public_key())


def test_message_codec_requires_peer_key_for_non_hello(codec: MessageCodec):
    message = Message(
        type=MessageType.NEW_TX,
        payload=NewTxPayload(transaction=_sample_transaction()),
    )
    raw = codec.encode(message, sender_node_id="node-local")
    with pytest.raises(ValueError, match="clave pública del peer"):
        codec.decode(raw, peer_public_key=None)


def test_decode_rejects_altered_signature(codec: MessageCodec, signer):
    message = Message(
        type=MessageType.GET_CHAIN,
        payload=GetChainPayload(since_height=1),
    )
    raw = bytearray(codec.encode(message, sender_node_id="node-local"))
    envelope = json.loads(bytes(raw).decode("utf-8"))
    signature = bytearray(envelope["signature"].encode("ascii"))
    signature[0] ^= 0x01
    envelope["signature"] = bytes(signature).decode("ascii")
    tampered = json.dumps(envelope).encode("utf-8")
    with pytest.raises(ValueError, match="Firma inválida"):
        codec.decode(tampered, peer_public_key=signer.get_public_key())


def test_hello_decodes_with_payload_public_key(codec: MessageCodec):
    node_public_key = codec._signer.get_public_key()
    message = Message(
        type=MessageType.HELLO,
        payload=HelloPayload(
            node_id="node-remote",
            public_key=bytes_to_b64(node_public_key),
            listen_port=9100,
        ),
    )
    raw = codec.encode(message, sender_node_id="node-remote")
    decoded = codec.decode(raw, peer_public_key=None)
    assert decoded.type == MessageType.HELLO
    assert decoded.payload.public_key == bytes_to_b64(node_public_key)


def test_decode_rejects_wrong_payload_shape(codec: MessageCodec, signer):
    wrong_payload = json.dumps({"since_height": 0}).encode("utf-8")
    payload_cipher = codec._encrypt(wrong_payload)
    envelope_firmable = {
        "sender_node_id": "node-local",
        "type": MessageType.NEW_TX.value,
        "payload_cipher": payload_cipher,
    }
    from main.infrastructure.serialization.canonical import json_canonical

    signature = codec._signer.sign(json_canonical(envelope_firmable))
    envelope = {
        **envelope_firmable,
        "signature": bytes_to_b64(signature),
    }
    tampered = json.dumps(envelope).encode("utf-8")
    with pytest.raises(ValueError, match="NEW_TX"):
        codec.decode(tampered, peer_public_key=signer.get_public_key())
