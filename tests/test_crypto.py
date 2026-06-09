"""Tests 1.1: cripto ISigner/IVerifier (doc/protocolo.md §1.1)."""

from cryptography.hazmat.primitives import serialization

from main.infrastructure.crypto.signer import CryptographySigner
from main.infrastructure.crypto.verifier import CryptographyVerifier
from main.infrastructure.serialization.canonical import b64_to_bytes


def test_sign_verify_round_trip(signer: CryptographySigner, verifier: CryptographyVerifier):
    payload = b"hashcoin-test-payload"
    signature = signer.sign(payload)
    public_key = signer.get_public_key()
    assert verifier.verify(payload, signature, public_key) is True


def test_verify_rejects_altered_signature(
    signer: CryptographySigner, verifier: CryptographyVerifier
):
    payload = b"hashcoin-test-payload"
    signature = bytearray(signer.sign(payload))
    signature[0] ^= 0x01
    assert verifier.verify(payload, bytes(signature), signer.get_public_key()) is False


def test_verify_rejects_wrong_public_key(
    signer: CryptographySigner,
    verifier: CryptographyVerifier,
):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    payload = b"hashcoin-test-payload"
    signature = signer.sign(payload)
    other_public_key = Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    assert verifier.verify(payload, signature, other_public_key) is False


def test_get_public_key_returns_loadable_der(signer: CryptographySigner):
    public_key = signer.get_public_key()
    loaded = serialization.load_der_public_key(public_key)
    assert loaded is not None
    assert public_key == signer.get_public_key()
