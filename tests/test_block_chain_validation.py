"""Tests 1.6: validación de bloque y cadena (doc/protocolo.md §5.3, §5.4)."""

from datetime import datetime, timezone

import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.domain.models.block import Block
from main.domain.models.transaction import Transaction
from main.infrastructure.crypto.verifier import CryptographyVerifier
from main.infrastructure.genesis.seed_genesis_provider import SeedGenesisProvider
from main.infrastructure.mining.proof_of_work import SHA256ProofOfWork
from main.infrastructure.serialization.canonical import (
    coinbase_id,
    derive_sender_id,
    transaction_firmable_bytes,
    transaction_id,
)
from main.infrastructure.validation.block_validator import DefaultBlockValidator
from main.infrastructure.validation.chain_verification_dispatcher import (
    ChainVerificationDispatcher,
)
from main.infrastructure.validation.chain_verifier import DefaultChainVerifier
from main.infrastructure.validation.transaction_validator import DefaultTransactionValidator

GENESIS_SEED = "test-seed"
DIFFICULTY = 1
MINING_REWARD = 50
MINING_ADDRESS = "miner" * 8
PREFUND_ACCOUNTS = 3
PREFUND_AMOUNT = 1000


def _genesis_provider() -> SeedGenesisProvider:
    return SeedGenesisProvider(GENESIS_SEED, PREFUND_ACCOUNTS, PREFUND_AMOUNT)


def _validators() -> tuple[
    DefaultTransactionValidator,
    DefaultBlockValidator,
    DefaultChainVerifier,
    SHA256ProofOfWork,
]:
    tx_validator = DefaultTransactionValidator(CryptographyVerifier())
    pow_service = SHA256ProofOfWork()
    block_validator = DefaultBlockValidator(
        pow_service, tx_validator, DIFFICULTY, MINING_REWARD, PREFUND_AMOUNT
    )
    chain_verifier = DefaultChainVerifier(block_validator, _genesis_provider())
    return tx_validator, block_validator, chain_verifier, pow_service


def _mine_block(
    pow_service: SHA256ProofOfWork,
    block_id: int,
    last_hash: str,
    previous_timestamp: datetime,
    transactions: list[Transaction],
) -> Block:
    candidate = Block(
        id=block_id,
        last_hash=last_hash,
        hash="",
        timestamp=datetime.fromtimestamp(
            previous_timestamp.timestamp() + 1.0, tz=timezone.utc
        ),
        target=DIFFICULTY,
        nonce=0,
        transactions=transactions,
    )
    result = pow_service.mine(candidate)
    candidate.nonce = result.nonce
    candidate.hash = result.block_hash
    return candidate


def _signed_tx_from_genesis(
    genesis: Block, receiver_id: str, amount: int
) -> tuple[Transaction, Ed25519PrivateKey]:
    funded = genesis.transactions[0].receiver_id
    import hashlib

    priv_seed = hashlib.sha256(f"{GENESIS_SEED}|prefund|{0}".encode()).digest()
    private_key = Ed25519PrivateKey.from_private_bytes(priv_seed)
    public_key_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    sender_id = derive_sender_id(public_key_der)
    assert sender_id == funded
    firmable = transaction_firmable_bytes(sender_id, receiver_id, amount)
    signature = private_key.sign(firmable)
    tx = Transaction(
        id=transaction_id(firmable, signature),
        sender_id=sender_id,
        receiver_id=receiver_id,
        amount=amount,
        signature=signature,
        public_key=public_key_der,
    )
    return tx, private_key


def test_valid_block_and_chain():
    _, block_validator, chain_verifier, pow_service = _validators()
    genesis = _genesis_provider().get_genesis_block()
    coinbase = Transaction(
        id=coinbase_id(1, MINING_ADDRESS, MINING_REWARD),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=MINING_REWARD,
        signature=b"",
        public_key=b"",
    )
    user_tx, _ = _signed_tx_from_genesis(genesis, "r" * 64, 100)
    mined = _mine_block(
        pow_service,
        block_id=1,
        last_hash=genesis.hash,
        previous_timestamp=genesis.timestamp,
        transactions=[coinbase, user_tx],
    )

    assert block_validator.validate_with_balances(
        mined, genesis.hash, balances={}
    ) is False

    balances: dict[str, int] = {}
    for tx in genesis.transactions:
        balances[tx.receiver_id] = balances.get(tx.receiver_id, 0) + tx.amount
    assert block_validator.validate_with_balances(mined, genesis.hash, balances) is True
    assert chain_verifier.verify_chain([genesis, mined]) is True


def test_invalid_last_hash_rejected():
    _, block_validator, _, pow_service = _validators()
    genesis = _genesis_provider().get_genesis_block()
    coinbase = Transaction(
        id=coinbase_id(1, MINING_ADDRESS, MINING_REWARD),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=MINING_REWARD,
        signature=b"",
        public_key=b"",
    )
    mined = _mine_block(
        pow_service, 1, "bad" * 16, genesis.timestamp, [coinbase]
    )
    balances: dict[str, int] = {}
    assert block_validator.validate_with_balances(mined, genesis.hash, balances) is False


def test_wrong_target_rejected():
    _, block_validator, _, pow_service = _validators()
    genesis = _genesis_provider().get_genesis_block()
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
    mined.target = 2
    balances: dict[str, int] = {}
    assert block_validator.validate_with_balances(mined, genesis.hash, balances) is False


def test_block_without_coinbase_rejected():
    _, block_validator, _, pow_service = _validators()
    genesis = _genesis_provider().get_genesis_block()
    user_tx, _ = _signed_tx_from_genesis(genesis, "r" * 64, 50)
    mined = _mine_block(
        pow_service, 1, genesis.hash, genesis.timestamp, [user_tx]
    )
    balances: dict[str, int] = {}
    for tx in genesis.transactions:
        balances[tx.receiver_id] = balances.get(tx.receiver_id, 0) + tx.amount
    assert block_validator.validate_with_balances(mined, genesis.hash, balances) is False


def test_coinbase_amount_must_match_mining_reward():
    _, block_validator, _, pow_service = _validators()
    genesis = _genesis_provider().get_genesis_block()
    bad_coinbase = Transaction(
        id=coinbase_id(1, MINING_ADDRESS, 10),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=10,
        signature=b"",
        public_key=b"",
    )
    mined = _mine_block(
        pow_service, 1, genesis.hash, genesis.timestamp, [bad_coinbase]
    )
    balances: dict[str, int] = {}
    assert block_validator.validate_with_balances(mined, genesis.hash, balances) is False


def test_non_increasing_timestamp_rejected_by_chain_verifier():
    _, _, chain_verifier, pow_service = _validators()
    genesis = _genesis_provider().get_genesis_block()
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
    assert chain_verifier.verify_chain([genesis, mined]) is False


def test_verify_chain_rejects_wrong_genesis():
    _, _, chain_verifier, _ = _validators()
    wrong_genesis = _genesis_provider().get_genesis_block()
    wrong_genesis.hash = "f" * 64
    assert chain_verifier.verify_chain([wrong_genesis]) is False


def test_verify_chain_rejects_broken_link():
    _, _, chain_verifier, pow_service = _validators()
    genesis = _genesis_provider().get_genesis_block()
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
    mined.last_hash = "b" * 64
    assert chain_verifier.verify_chain([genesis, mined]) is False


def test_verify_chain_rejects_duplicate_transaction():
    _, _, chain_verifier, pow_service = _validators()
    genesis = _genesis_provider().get_genesis_block()
    user_tx, _ = _signed_tx_from_genesis(genesis, "r" * 64, 50)
    coinbase1 = Transaction(
        id=coinbase_id(1, MINING_ADDRESS, MINING_REWARD),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=MINING_REWARD,
        signature=b"",
        public_key=b"",
    )
    block1 = _mine_block(
        pow_service, 1, genesis.hash, genesis.timestamp, [coinbase1, user_tx]
    )
    coinbase2 = Transaction(
        id=coinbase_id(2, MINING_ADDRESS, MINING_REWARD),
        sender_id="COINBASE",
        receiver_id=MINING_ADDRESS,
        amount=MINING_REWARD,
        signature=b"",
        public_key=b"",
    )
    block2 = _mine_block(
        pow_service, 2, block1.hash, block1.timestamp, [coinbase2, user_tx]
    )
    assert chain_verifier.verify_chain([genesis, block1, block2]) is False


@pytest.mark.asyncio
async def test_chain_verification_dispatcher_returns_result() -> None:
    _, _, chain_verifier, _ = _validators()
    dispatcher = ChainVerificationDispatcher(chain_verifier, workers=1)
    dispatcher.start()
    try:
        genesis = _genesis_provider().get_genesis_block()
        result = await dispatcher.verify([genesis])
        assert result is True
    finally:
        dispatcher.stop()
