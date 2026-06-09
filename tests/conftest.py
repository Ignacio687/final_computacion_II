"""Fixtures compartidas para tests unitarios de HashCoin."""

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.infrastructure.crypto.signer import CryptographySigner
from main.infrastructure.crypto.verifier import CryptographyVerifier
from main.infrastructure.serialization.message_codec import MessageCodec


@pytest.fixture
def shared_key() -> bytes:
    return b"\x00" * 32


@pytest.fixture
def ed25519_keypair(tmp_path) -> tuple[Ed25519PrivateKey, bytes]:
    private_key = Ed25519PrivateKey.generate()
    public_key_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    return private_key, public_key_der


@pytest.fixture
def signer(ed25519_keypair, tmp_path) -> CryptographySigner:
    private_key, _ = ed25519_keypair
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path = tmp_path / "node_private.pem"
    public_path = tmp_path / "node_public.pem"
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    return CryptographySigner(str(private_path), str(public_path))


@pytest.fixture
def verifier() -> CryptographyVerifier:
    return CryptographyVerifier()


@pytest.fixture
def codec(signer, verifier, shared_key) -> MessageCodec:
    return MessageCodec(signer, verifier, shared_key)
