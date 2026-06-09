"""Tests 1.7: génesis determinista (doc/protocolo.md §8)."""

import hashlib

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.infrastructure.genesis.seed_genesis_provider import SeedGenesisProvider
from main.infrastructure.serialization.canonical import (
    derive_sender_id,
    transaction_firmable_bytes,
    transaction_id,
)

GENESIS_SEED = "test-seed"
PREFUND_ACCOUNTS = 3
PREFUND_AMOUNT = 1000


def _derive_prefund_account(seed: str, index: int) -> tuple[str, bytes, Ed25519PrivateKey]:
    priv_seed = hashlib.sha256(f"{seed}|prefund|{index}".encode()).digest()
    private_key = Ed25519PrivateKey.from_private_bytes(priv_seed)
    public_key_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return derive_sender_id(public_key_der), public_key_der, private_key


def test_same_seed_produces_same_genesis_hash():
    provider_a = SeedGenesisProvider(GENESIS_SEED, PREFUND_ACCOUNTS, PREFUND_AMOUNT)
    provider_b = SeedGenesisProvider(GENESIS_SEED, PREFUND_ACCOUNTS, PREFUND_AMOUNT)
    assert provider_a.get_genesis_block().hash == provider_b.get_genesis_block().hash


def test_different_seeds_produce_different_hashes():
    provider_a = SeedGenesisProvider("seed-a", PREFUND_ACCOUNTS, PREFUND_AMOUNT)
    provider_b = SeedGenesisProvider("seed-b", PREFUND_ACCOUNTS, PREFUND_AMOUNT)
    assert provider_a.get_genesis_block().hash != provider_b.get_genesis_block().hash


def test_prefund_addresses_match_derivation_and_can_sign():
    provider = SeedGenesisProvider(GENESIS_SEED, PREFUND_ACCOUNTS, PREFUND_AMOUNT)
    genesis = provider.get_genesis_block()

    for index, tx in enumerate(genesis.transactions):
        assert tx.sender_id == "GENESIS"
        address, public_key_der, private_key = _derive_prefund_account(GENESIS_SEED, index)
        assert tx.receiver_id == address
        assert tx.amount == PREFUND_AMOUNT

        receiver_id = "r" * 64
        firmable = transaction_firmable_bytes(address, receiver_id, 10)
        signature = private_key.sign(firmable)
        assert transaction_id(firmable, signature)
        assert public_key_der == _derive_prefund_account(GENESIS_SEED, index)[1]
