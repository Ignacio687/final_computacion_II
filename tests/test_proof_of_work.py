"""Tests 1.5: PoW (doc/protocolo.md §5.2)."""

from datetime import datetime, timezone

from main.domain.models.block import Block
from main.domain.models.transaction import Transaction
from main.infrastructure.mining.proof_of_work import SHA256ProofOfWork
from main.infrastructure.serialization.canonical import coinbase_id


def _coinbase(height: int, mining_address: str, reward: int) -> Transaction:
    return Transaction(
        id=coinbase_id(height, mining_address, reward),
        sender_id="COINBASE",
        receiver_id=mining_address,
        amount=reward,
        signature=b"",
        public_key=b"",
    )


def _candidate_block(target: int = 1) -> Block:
    mining_address = "m" * 64
    return Block(
        id=1,
        last_hash="a" * 64,
        hash="",
        timestamp=datetime.fromtimestamp(1700000000.0, tz=timezone.utc),
        target=target,
        nonce=0,
        transactions=[_coinbase(1, mining_address, 50)],
    )


def test_mine_returns_valid_pow():
    pow_service = SHA256ProofOfWork()
    candidate = _candidate_block(target=1)
    result = pow_service.mine(candidate)
    candidate.nonce = result.nonce
    candidate.hash = result.block_hash
    assert result.block_hash.startswith("0" * candidate.target)
    assert pow_service.verify(candidate) is True


def test_verify_rejects_tampered_hash_or_nonce():
    pow_service = SHA256ProofOfWork()
    candidate = _candidate_block(target=1)
    result = pow_service.mine(candidate)
    candidate.nonce = result.nonce
    candidate.hash = result.block_hash

    tampered_hash = Block(
        id=candidate.id,
        last_hash=candidate.last_hash,
        hash="f" * 64,
        timestamp=candidate.timestamp,
        target=candidate.target,
        nonce=candidate.nonce,
        transactions=candidate.transactions,
    )
    assert pow_service.verify(tampered_hash) is False

    tampered_nonce = Block(
        id=candidate.id,
        last_hash=candidate.last_hash,
        hash=candidate.hash,
        timestamp=candidate.timestamp,
        target=candidate.target,
        nonce=candidate.nonce + 1,
        transactions=candidate.transactions,
    )
    assert pow_service.verify(tampered_nonce) is False
