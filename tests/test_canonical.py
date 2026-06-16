"""Tests 1.2: direcciones e IDs (doc/protocolo.md §2, §3)."""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.infrastructure.serialization.canonical import (
    derive_sender_id,
    json_canonical,
    sha256_hex,
    transaction_firmable_bytes,
    transaction_id,
)


def _public_key_der(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def test_sender_id_is_deterministic():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    assert derive_sender_id(public_key_der) == derive_sender_id(public_key_der)
    assert derive_sender_id(public_key_der) == sha256_hex(public_key_der)


def test_transaction_firmable_bytes_are_canonical_json():
    sender_id = "a" * 64
    receiver_id = "b" * 64
    amount = 100
    firmable = transaction_firmable_bytes(sender_id, receiver_id, amount)
    assert firmable == json_canonical(
        {
            "amount": amount,
            "receiver_id": receiver_id,
            "sender_id": sender_id,
        }
    )


def test_transaction_id_is_reproducible():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    receiver_id = "c" * 64
    amount = 250
    firmable = transaction_firmable_bytes(sender_id, receiver_id, amount)
    signature = private_key.sign(firmable)
    expected_id = sha256_hex(firmable + signature)
    assert transaction_id(firmable, signature) == expected_id
    assert transaction_id(firmable, signature) == transaction_id(firmable, signature)
