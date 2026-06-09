"""Tests 1.3: mappers DTO <-> dominio (doc/protocolo.md §1, §3-§5)."""

from datetime import datetime, timezone

from main.domain.models.block import Block
from main.domain.models.transaction import Transaction
from main.repository.dto.block_dto import BlockDTO
from main.repository.dto.mappers import (
    block_from_dto,
    block_to_dto,
    transaction_from_dto,
    transaction_to_dto,
)
from main.repository.dto.transaction_dto import TransactionDTO


def test_transaction_dto_round_trip():
    tx = Transaction(
        id="tx-id-1",
        sender_id="a" * 64,
        receiver_id="b" * 64,
        amount=42,
        signature=b"\x01\x02\x03",
        public_key=b"\x04\x05\x06",
    )
    dto = transaction_to_dto(tx)
    restored = transaction_from_dto(dto)
    assert restored == tx
    assert dto.signature != ""
    assert dto.public_key != ""


def test_block_dto_round_trip():
    tx = Transaction(
        id="tx-id-2",
        sender_id="COINBASE",
        receiver_id="d" * 64,
        amount=50,
        signature=b"",
        public_key=b"",
    )
    timestamp = datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
    block = Block(
        id=1,
        last_hash="0" * 64,
        hash="f" * 64,
        timestamp=timestamp,
        target=2,
        nonce=7,
        transactions=[tx],
    )
    dto = block_to_dto(block)
    restored = block_from_dto(dto)
    assert restored.id == block.id
    assert restored.last_hash == block.last_hash
    assert restored.hash == block.hash
    assert restored.timestamp == block.timestamp
    assert restored.target == block.target
    assert restored.nonce == block.nonce
    assert restored.transactions == block.transactions
    assert dto.timestamp == timestamp.timestamp()
