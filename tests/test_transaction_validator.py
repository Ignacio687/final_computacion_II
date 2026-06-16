"""Tests 1.4: validación de transacción (doc/protocolo.md §3.3)."""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.domain.models.transaction import Transaction
from main.infrastructure.crypto.verifier import CryptographyVerifier
from main.infrastructure.serialization.canonical import (
    coinbase_id,
    derive_sender_id,
    genesis_tx_id,
    transaction_firmable_bytes,
    transaction_id,
)
from main.infrastructure.validation.transaction_validator import DefaultTransactionValidator


class InMemoryTransactionRepository:
    def __init__(self, balances: dict[str, int] | None = None) -> None:
        self._balances = dict(balances or {})
        self._known_ids: set[str] = set()
        self._mempool: list[Transaction] = []

    def add_to_mempool(self, tx: Transaction) -> None:
        self._mempool.append(tx)

    def get_mempool(self) -> list[Transaction]:
        return list(self._mempool)

    def remove_from_mempool(self, tx_ids: list[str]) -> None:
        pass

    def exists_in_mempool_or_chain(self, tx_id: str) -> bool:
        return tx_id in self._known_ids

    def get_balance(self, address: str) -> int:
        return self._balances.get(address, 0)

    def get_transactions_for_address(self, address: str, limit: int) -> list[Transaction]:
        return []

    def get_recent_transactions(self, limit: int) -> list[Transaction]:
        return []

    def get_total_supply(self) -> int:
        return sum(self._balances.values())

    def get_active_accounts(self, limit: int) -> list:
        return []

    def mark_known(self, tx_id: str) -> None:
        self._known_ids.add(tx_id)


def _public_key_der(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _signed_tx(
    private_key: Ed25519PrivateKey,
    receiver_id: str,
    amount: int,
) -> Transaction:
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    firmable = transaction_firmable_bytes(sender_id, receiver_id, amount)
    signature = private_key.sign(firmable)
    return Transaction(
        id=transaction_id(firmable, signature),
        sender_id=sender_id,
        receiver_id=receiver_id,
        amount=amount,
        signature=signature,
        public_key=public_key_der,
    )


def test_valid_signed_transaction_with_sufficient_balance():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    repo = InMemoryTransactionRepository({sender_id: 1000})
    validator = DefaultTransactionValidator(CryptographyVerifier(), repo)
    tx = _signed_tx(private_key, "b" * 64, 100)
    assert validator.validate(tx) is True


def test_invalid_signature_rejected():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    repo = InMemoryTransactionRepository({sender_id: 1000})
    validator = DefaultTransactionValidator(CryptographyVerifier(), repo)
    tx = _signed_tx(private_key, "b" * 64, 100)
    tx.signature = b"\x00" * 64
    assert validator.validate(tx) is False


def test_sender_id_must_derive_from_public_key():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    repo = InMemoryTransactionRepository({sender_id: 1000})
    validator = DefaultTransactionValidator(CryptographyVerifier(), repo)
    tx = _signed_tx(private_key, "b" * 64, 100)
    tx.sender_id = "a" * 64
    assert validator.validate(tx) is False


def test_non_positive_amount_rejected():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    repo = InMemoryTransactionRepository({sender_id: 1000})
    validator = DefaultTransactionValidator(CryptographyVerifier(), repo)
    tx = _signed_tx(private_key, "b" * 64, 0)
    assert validator.validate(tx) is False


def test_negative_amount_rejected():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    repo = InMemoryTransactionRepository({sender_id: 1000})
    validator = DefaultTransactionValidator(CryptographyVerifier(), repo)
    tx = _signed_tx(private_key, "b" * 64, -1)
    assert validator.validate(tx) is False


def test_transaction_validator_rejects_duplicate_id():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    repo = InMemoryTransactionRepository({sender_id: 1000})
    tx = _signed_tx(private_key, "b" * 64, 100)
    repo.mark_known(tx.id)
    validator = DefaultTransactionValidator(CryptographyVerifier(), repo)
    assert validator.validate(tx) is False


def test_insufficient_balance_rejected():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    repo = InMemoryTransactionRepository({sender_id: 50})
    validator = DefaultTransactionValidator(CryptographyVerifier(), repo)
    tx = _signed_tx(private_key, "b" * 64, 100)
    assert validator.validate(tx) is False


def test_second_tx_same_sender_rejected_when_mempool_has_pending():
    private_key = Ed25519PrivateKey.generate()
    public_key_der = _public_key_der(private_key)
    sender_id = derive_sender_id(public_key_der)
    repo = InMemoryTransactionRepository({sender_id: 1000})
    validator = DefaultTransactionValidator(CryptographyVerifier(), repo)
    tx1 = _signed_tx(private_key, "b" * 64, 800)
    tx2 = _signed_tx(private_key, "c" * 64, 300)
    repo.add_to_mempool(tx1)
    assert validator.validate(tx1) is True
    assert validator.validate(tx2) is False


def test_coinbase_and_genesis_rejected_from_mempool():
    validator = DefaultTransactionValidator(CryptographyVerifier())
    coinbase = Transaction(
        id=coinbase_id(1, "miner" * 8, 50),
        sender_id="COINBASE",
        receiver_id="miner" * 8,
        amount=50,
        signature=b"",
        public_key=b"",
    )
    genesis = Transaction(
        id=genesis_tx_id(0, "a" * 64, 1000),
        sender_id="GENESIS",
        receiver_id="a" * 64,
        amount=1000,
        signature=b"",
        public_key=b"",
    )
    assert validator.validate(coinbase) is False
    assert validator.validate(genesis) is False
