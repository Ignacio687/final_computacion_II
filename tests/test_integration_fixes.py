"""Tests unitarios para fixes de integración (mempool, TCP, mining, timestamp)."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from main.domain.models.block import Block
from main.domain.models.transaction import Transaction
from main.infrastructure.crypto.verifier import CryptographyVerifier
from main.infrastructure.genesis.seed_genesis_provider import SeedGenesisProvider
from main.infrastructure.mining.proof_of_work import SHA256ProofOfWork
from main.infrastructure.serialization.canonical import coinbase_id
from main.infrastructure.tcp.tcp_message_sender import TCPMessageSender
from main.infrastructure.validation.block_validator import (
    DefaultBlockValidator,
    balances_from_chain,
)
from main.infrastructure.validation.transaction_validator import DefaultTransactionValidator
from main.service.mining_service import MiningService
from tests.test_block_chain_validation import (
    DIFFICULTY,
    GENESIS_SEED,
    MINING_ADDRESS,
    MINING_REWARD,
    PREFUND_ACCOUNTS,
    PREFUND_AMOUNT,
    _mine_block,
    _signed_tx_from_genesis,
)
from tests.test_transaction_validator import InMemoryTransactionRepository


def _genesis() -> Block:
    return SeedGenesisProvider(
        GENESIS_SEED, PREFUND_ACCOUNTS, PREFUND_AMOUNT
    ).get_genesis_block()


def test_block_validator_rejects_non_increasing_timestamp():
    genesis = _genesis()
    pow_service = SHA256ProofOfWork()
    block_validator = DefaultBlockValidator(
        pow_service,
        DefaultTransactionValidator(CryptographyVerifier()),
        DIFFICULTY,
        MINING_REWARD,
        PREFUND_AMOUNT,
    )
    coinbase = Transaction(
        id=coinbase_id(1, MINING_ADDRESS, MINING_REWARD),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=MINING_REWARD,
        signature=b"",
        public_key=b"",
    )
    mined = _mine_block(
        pow_service, 1, genesis.hash, genesis.timestamp, [coinbase]
    )
    mined.timestamp = genesis.timestamp
    balances = balances_from_chain([genesis])
    assert block_validator.validate_with_balances(
        mined, genesis.hash, balances, previous_timestamp=genesis.timestamp
    ) is False


def test_mined_block_validation_accepts_tx_in_local_mempool():
    genesis = _genesis()
    user_tx, _ = _signed_tx_from_genesis(genesis, "r" * 64, 100)
    repo = InMemoryTransactionRepository(
        balances={user_tx.sender_id: 1000}
    )
    repo.mark_known(user_tx.id)
    assert DefaultTransactionValidator(CryptographyVerifier(), repo).validate(
        user_tx
    ) is False

    pow_service = SHA256ProofOfWork()
    block_validator = DefaultBlockValidator(
        pow_service,
        DefaultTransactionValidator(CryptographyVerifier(), repo),
        DIFFICULTY,
        MINING_REWARD,
        PREFUND_AMOUNT,
    )
    coinbase = Transaction(
        id=coinbase_id(1, MINING_ADDRESS, MINING_REWARD),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=MINING_REWARD,
        signature=b"",
        public_key=b"",
    )
    mined = _mine_block(
        pow_service, 1, genesis.hash, genesis.timestamp, [coinbase, user_tx]
    )
    balances = balances_from_chain([genesis])
    assert block_validator.validate_with_balances(
        mined, genesis.hash, balances, previous_timestamp=genesis.timestamp
    ) is True


def test_unregister_incoming_skips_stale_writer():
    sender = TCPMessageSender(
        peers=[],
        signer=MagicMock(),
        codec=MagicMock(),
        node_id="node-a",
        listen_port=9000,
        reconnect_delay_seconds=1.0,
    )
    writer_old = MagicMock()
    writer_new = MagicMock()
    reader = MagicMock()
    public_key = b"key"

    sender.register_incoming("peer-1", "127.0.0.1", 9001, reader, writer_old, public_key)
    sender.register_incoming("peer-1", "127.0.0.1", 9001, reader, writer_new, public_key)
    sender.unregister_incoming("peer-1", writer_old)

    assert sender._incoming["peer-1"].writer is writer_new


@pytest.mark.asyncio
async def test_mining_discards_stale_candidate_after_pow():
    genesis = _genesis()
    user_tx, _ = _signed_tx_from_genesis(genesis, "r" * 64, 50)
    pow_service = SHA256ProofOfWork()
    block_validator = DefaultBlockValidator(
        pow_service,
        DefaultTransactionValidator(CryptographyVerifier()),
        DIFFICULTY,
        MINING_REWARD,
        PREFUND_AMOUNT,
    )

    coinbase1 = Transaction(
        id=coinbase_id(1, MINING_ADDRESS, MINING_REWARD),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=MINING_REWARD,
        signature=b"",
        public_key=b"",
    )
    competing = _mine_block(
        pow_service, 1, genesis.hash, genesis.timestamp, [coinbase1, user_tx]
    )

    chain_state = [genesis]

    class FakeBlockchainRepository:
        def get_last_block(self) -> Block | None:
            return chain_state[-1]

        def get_chain(self) -> list[Block]:
            return list(chain_state)

        def append_block(self, block: Block) -> None:
            chain_state.append(block)

    blockchain_repo = FakeBlockchainRepository()
    mempool = [user_tx]

    class FakeTransactionRepository:
        def get_mempool(self) -> list[Transaction]:
            return list(mempool)

        def remove_from_mempool(self, tx_ids: list[str]) -> None:
            mempool[:] = [tx for tx in mempool if tx.id not in tx_ids]

    message_sender = MagicMock()
    message_sender.broadcast = AsyncMock()

    service = MiningService(
        blockchain_repo,
        FakeTransactionRepository(),
        pow_service,
        block_validator,
        message_sender,
        pool=None,
        difficulty=DIFFICULTY,
        min_transactions_per_block=1,
        block_interval_seconds=0.0,
        mining_reward=MINING_REWARD,
        mining_address=MINING_ADDRESS,
        chain_lock=asyncio.Lock(),
    )
    service._last_attempt = None

    loop = asyncio.get_running_loop()
    original_run_in_executor = loop.run_in_executor

    async def fake_run_in_executor(pool, func, candidate):
        chain_state.append(competing)
        return await original_run_in_executor(pool, func, candidate)

    loop.run_in_executor = fake_run_in_executor  # type: ignore[method-assign]
    try:
        await service.try_mine()
    finally:
        loop.run_in_executor = original_run_in_executor  # type: ignore[method-assign]

    assert chain_state == [genesis, competing]
    message_sender.broadcast.assert_not_called()
