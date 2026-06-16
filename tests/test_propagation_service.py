"""Tests unitarios de PropagationService (Bloque C)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from main.domain.models.block import Block
from main.domain.models.message import Message, MessageType
from main.domain.models.node_info import NodeInfo
from main.domain.models.payloads import NewBlockPayload, NewTxPayload
from main.domain.models.transaction import Transaction
from main.infrastructure.crypto.verifier import CryptographyVerifier
from main.infrastructure.genesis.seed_genesis_provider import SeedGenesisProvider
from main.infrastructure.mining.proof_of_work import SHA256ProofOfWork
from main.infrastructure.serialization.canonical import coinbase_id
from main.infrastructure.validation.block_validator import DefaultBlockValidator
from main.infrastructure.validation.chain_verification_dispatcher import (
    ChainVerificationDispatcher,
)
from main.infrastructure.validation.chain_verifier import DefaultChainVerifier
from main.infrastructure.validation.transaction_validator import DefaultTransactionValidator
from main.repository.dto.mappers import block_to_dto, transaction_to_dto
from main.service.propagation_service import PropagationService
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


def _build_propagation_service(
    *,
    blockchain_repo: MagicMock | None = None,
    transaction_repo: MagicMock | None = None,
    message_sender: MagicMock | None = None,
) -> tuple[PropagationService, MagicMock, MagicMock, MagicMock]:
    genesis = _genesis()
    if blockchain_repo is None:
        blockchain_repo = MagicMock()
        blockchain_repo.get_height.return_value = 1
        blockchain_repo.get_last_block.return_value = genesis
        blockchain_repo.get_chain.return_value = [genesis]
        blockchain_repo.append_block.return_value = True
    if transaction_repo is None:
        transaction_repo = MagicMock()
        transaction_repo.exists_in_mempool_or_chain.return_value = False
    if message_sender is None:
        message_sender = MagicMock()
        message_sender.broadcast = AsyncMock()
        message_sender.send_to_peer = AsyncMock()

    tx_validator = DefaultTransactionValidator(CryptographyVerifier(), transaction_repo)
    pow_service = SHA256ProofOfWork()
    block_validator = DefaultBlockValidator(
        pow_service,
        tx_validator,
        DIFFICULTY,
        MINING_REWARD,
        PREFUND_AMOUNT,
    )
    chain_verifier = DefaultChainVerifier(
        block_validator, SeedGenesisProvider(GENESIS_SEED, PREFUND_ACCOUNTS, PREFUND_AMOUNT)
    )
    chain_dispatcher = ChainVerificationDispatcher(chain_verifier, workers=1)
    service = PropagationService(
        blockchain_repo,
        transaction_repo,
        tx_validator,
        block_validator,
        chain_dispatcher,
        message_sender,
        asyncio.Lock(),
    )
    return service, blockchain_repo, transaction_repo, message_sender


@pytest.mark.asyncio
async def test_propagation_new_tx_valid_adds_to_mempool():
    genesis = _genesis()
    user_tx, _ = _signed_tx_from_genesis(genesis, "r" * 64, 50)
    mempool: list[Transaction] = []

    transaction_repo = MagicMock()
    transaction_repo.exists_in_mempool_or_chain.return_value = False
    transaction_repo.get_balance.return_value = PREFUND_AMOUNT
    transaction_repo.get_mempool.return_value = mempool

    def add_to_mempool(tx: Transaction) -> None:
        mempool.append(tx)

    transaction_repo.add_to_mempool.side_effect = add_to_mempool

    service, _, transaction_repo, message_sender = _build_propagation_service(
        transaction_repo=transaction_repo,
    )
    peer = NodeInfo(host="127.0.0.1", port=9001, node_id="peer-a")
    message = Message(
        type=MessageType.NEW_TX,
        payload=NewTxPayload(transaction=transaction_to_dto(user_tx)),
    )

    await service.handle_message(peer, message)

    transaction_repo.add_to_mempool.assert_called_once()
    assert mempool[0].id == user_tx.id
    message_sender.broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_propagation_new_tx_duplicate_ignored():
    genesis = _genesis()
    user_tx, _ = _signed_tx_from_genesis(genesis, "r" * 64, 50)

    transaction_repo = MagicMock()
    transaction_repo.exists_in_mempool_or_chain.return_value = True

    service, _, transaction_repo, message_sender = _build_propagation_service(
        transaction_repo=transaction_repo,
    )
    peer = NodeInfo(host="127.0.0.1", port=9001, node_id="peer-a")
    message = Message(
        type=MessageType.NEW_TX,
        payload=NewTxPayload(transaction=transaction_to_dto(user_tx)),
    )

    await service.handle_message(peer, message)

    transaction_repo.add_to_mempool.assert_not_called()
    message_sender.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_propagation_append_block_false_does_not_broadcast():
    genesis = _genesis()
    user_tx, _ = _signed_tx_from_genesis(genesis, "r" * 64, 50)
    pow_service = SHA256ProofOfWork()
    coinbase = Transaction(
        id=coinbase_id(1, MINING_ADDRESS, MINING_REWARD),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=MINING_REWARD,
        signature=b"",
        public_key=b"",
    )
    block = _mine_block(
        pow_service, 1, genesis.hash, genesis.timestamp, [coinbase, user_tx]
    )

    blockchain_repo = MagicMock()
    blockchain_repo.get_height.return_value = 0
    blockchain_repo.get_last_block.return_value = genesis
    blockchain_repo.get_chain.return_value = [genesis]
    blockchain_repo.append_block.return_value = False

    transaction_repo = MagicMock()
    transaction_repo.exists_in_mempool_or_chain.return_value = False
    transaction_repo.get_balance.return_value = PREFUND_AMOUNT
    transaction_repo.get_mempool.return_value = []

    service, blockchain_repo, transaction_repo, message_sender = _build_propagation_service(
        blockchain_repo=blockchain_repo,
        transaction_repo=transaction_repo,
    )
    peer = NodeInfo(host="127.0.0.1", port=9001, node_id="peer-a")
    message = Message(
        type=MessageType.NEW_BLOCK,
        payload=NewBlockPayload(block=block_to_dto(block)),
    )

    await service.handle_message(peer, message)

    blockchain_repo.append_block.assert_called_once()
    transaction_repo.remove_from_mempool.assert_not_called()
    message_sender.broadcast.assert_not_awaited()
