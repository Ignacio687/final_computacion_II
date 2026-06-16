"""Tests 1.9: repositorios SQLite (doc/protocolo.md §7, §11)."""

from datetime import datetime, timezone

import pytest

from main.domain.models.block import Block
from main.domain.models.transaction import Transaction
from main.infrastructure.persistence.sqlite.blockchain_repository import SQLiteBlockchainRepository
from main.infrastructure.persistence.sqlite.transaction_repository import SQLiteTransactionRepository
from main.infrastructure.serialization.canonical import (
    block_hash,
    coinbase_id,
    genesis_tx_id,
)


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture
def blockchain_repo(db_path) -> SQLiteBlockchainRepository:
    return SQLiteBlockchainRepository(db_path)


@pytest.fixture
def transaction_repo(db_path) -> SQLiteTransactionRepository:
    return SQLiteTransactionRepository(db_path)


def _genesis_block() -> Block:
    addr_a = "a" * 64
    addr_b = "b" * 64
    txs = [
        Transaction(
            id=genesis_tx_id(0, addr_a, 1000),
            sender_id="GENESIS",
            receiver_id=addr_a,
            amount=1000,
            signature=b"",
            public_key=b"",
        ),
        Transaction(
            id=genesis_tx_id(1, addr_b, 1000),
            sender_id="GENESIS",
            receiver_id=addr_b,
            amount=1000,
            signature=b"",
            public_key=b"",
        ),
    ]
    timestamp = 0.0
    block_hash_value = block_hash("0" * 64, timestamp, 0, 0, [tx.id for tx in txs])
    return Block(
        id=0,
        last_hash="0" * 64,
        hash=block_hash_value,
        timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
        target=0,
        nonce=0,
        transactions=txs,
    )


def _signed_tx(
    tx_id: str,
    sender: str,
    receiver: str,
    amount: int,
    signature: bytes = b"\xaa",
    public_key: bytes = b"\xbb",
) -> Transaction:
    return Transaction(
        id=tx_id,
        sender_id=sender,
        receiver_id=receiver,
        amount=amount,
        signature=signature,
        public_key=public_key,
    )


def _mined_block(
    height: int,
    last_hash: str,
    mining_address: str,
    mining_reward: int,
    mempool_txs: list[Transaction],
    timestamp_epoch: float,
    target: int = 0,
    nonce: int = 0,
) -> Block:
    coinbase = Transaction(
        id=coinbase_id(height, mining_address, mining_reward),
        sender_id="COINBASE",
        receiver_id=mining_address,
        amount=mining_reward,
        signature=b"",
        public_key=b"",
    )
    txs = [coinbase, *mempool_txs]
    block_hash_value = block_hash(last_hash, timestamp_epoch, target, nonce, [tx.id for tx in txs])
    return Block(
        id=height,
        last_hash=last_hash,
        hash=block_hash_value,
        timestamp=datetime.fromtimestamp(timestamp_epoch, tz=timezone.utc),
        target=target,
        nonce=nonce,
        transactions=txs,
    )


def test_append_block_persists_and_clears_mempool(
    blockchain_repo, transaction_repo, db_path
):
    genesis = _genesis_block()
    blockchain_repo.append_block(genesis)
    assert blockchain_repo.get_height() == 0
    assert blockchain_repo.get_last_block() == genesis

    chain = blockchain_repo.get_chain()
    assert len(chain) == 1
    assert chain[0].id == 0
    assert len(chain[0].transactions) == 2

    addr_a = "a" * 64
    addr_b = "b" * 64
    pending = _signed_tx("pending-tx", addr_a, addr_b, 100)
    transaction_repo.add_to_mempool(pending)
    assert transaction_repo.get_mempool() == [pending]

    block1 = _mined_block(
        height=1,
        last_hash=genesis.hash,
        mining_address="m" * 64,
        mining_reward=50,
        mempool_txs=[pending],
        timestamp_epoch=1.0,
    )
    blockchain_repo.append_block(block1)

    assert blockchain_repo.get_height() == 1
    assert blockchain_repo.get_last_block().id == 1
    assert transaction_repo.get_mempool() == []
    assert blockchain_repo.get_chain_since(1) == [block1]


def test_get_balance_on_confirmed_transactions(blockchain_repo, transaction_repo):
    genesis = _genesis_block()
    blockchain_repo.append_block(genesis)

    addr_a = "a" * 64
    addr_b = "b" * 64
    miner = "m" * 64

    assert transaction_repo.get_balance(addr_a) == 1000
    assert transaction_repo.get_balance(addr_b) == 1000
    assert transaction_repo.get_balance(miner) == 0

    spend = _signed_tx("spend-tx", addr_a, addr_b, 300)
    block1 = _mined_block(1, genesis.hash, miner, 50, [spend], 1.0)
    blockchain_repo.append_block(block1)

    assert transaction_repo.get_balance(addr_a) == 700
    assert transaction_repo.get_balance(addr_b) == 1300
    assert transaction_repo.get_balance(miner) == 50
    assert transaction_repo.get_total_supply() == 2000 + 50


def test_get_active_accounts_ordered_by_recent_activity(
    blockchain_repo, transaction_repo
):
    genesis = _genesis_block()
    blockchain_repo.append_block(genesis)

    addr_a = "a" * 64
    addr_b = "b" * 64
    addr_c = "c" * 64
    miner = "m" * 64

    block1 = _mined_block(
        1, genesis.hash, miner, 50, [_signed_tx("tx1", addr_a, addr_b, 100)], 1.0
    )
    blockchain_repo.append_block(block1)
    block2 = _mined_block(
        2, block1.hash, miner, 50, [_signed_tx("tx2", addr_b, addr_c, 25)], 2.0
    )
    blockchain_repo.append_block(block2)

    active = transaction_repo.get_active_accounts(20)
    assert len(active) == 4
    top_two = {active[0].address, active[1].address}
    assert top_two == {addr_b, addr_c}
    assert active[0].last_block_id == 2
    balances = {account.address: account.balance for account in active}
    assert balances[addr_c] == 25
    assert balances[addr_b] == 1075


def test_exists_in_mempool_or_chain(blockchain_repo, transaction_repo):
    genesis = _genesis_block()
    blockchain_repo.append_block(genesis)

    genesis_tx_id_value = genesis.transactions[0].id
    assert transaction_repo.exists_in_mempool_or_chain(genesis_tx_id_value)
    assert not transaction_repo.exists_in_mempool_or_chain("unknown-tx")

    pending = _signed_tx("mempool-tx", "a" * 64, "b" * 64, 10)
    transaction_repo.add_to_mempool(pending)
    assert transaction_repo.exists_in_mempool_or_chain("mempool-tx")


def test_append_block_returns_false_on_duplicate_hash(blockchain_repo):
    genesis = _genesis_block()
    assert blockchain_repo.append_block(genesis) is True
    assert blockchain_repo.append_block(genesis) is False
    assert blockchain_repo.get_height() == 0


def test_replace_chain_is_atomic(blockchain_repo, transaction_repo):
    genesis = _genesis_block()
    blockchain_repo.append_block(genesis)

    addr_a = "a" * 64
    addr_b = "b" * 64
    miner = "m" * 64
    spend = _signed_tx("spend-tx", addr_a, addr_b, 200)
    transaction_repo.add_to_mempool(spend)

    block1 = _mined_block(1, genesis.hash, miner, 50, [spend], 1.0)
    blockchain_repo.append_block(block1)
    assert transaction_repo.get_mempool() == []

    alt_block1 = _mined_block(1, genesis.hash, miner, 50, [], 2.0, nonce=1)
    blockchain_repo.replace_chain([genesis, alt_block1])

    chain = blockchain_repo.get_chain()
    assert len(chain) == 2
    assert chain[1].hash == alt_block1.hash
    assert blockchain_repo.get_height() == 1

    mempool = transaction_repo.get_mempool()
    assert len(mempool) == 1
    assert mempool[0].id == "spend-tx"
    assert transaction_repo.get_balance(addr_a) == 1000
    assert transaction_repo.get_balance(addr_b) == 1000
