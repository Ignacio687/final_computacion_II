"""Adaptador: validación de bloques (hash, PoW, transacciones). Ver doc/protocolo.md §5.3."""

from datetime import datetime
from typing import Dict, List, Optional

from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.proof_of_work import IProofOfWork
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.domain.models.block import Block
from main.infrastructure.serialization.canonical import block_hash
from main.infrastructure.validation.transaction_validator import (
    COINBASE_SENDER,
    GENESIS_SENDER,
    DefaultTransactionValidator,
)

GENESIS_HEIGHT = 0
GENESIS_LAST_HASH = "0" * 64
GENESIS_TIMESTAMP_EPOCH = 0.0
GENESIS_NONCE = 0


def balances_from_chain(chain: List[Block]) -> Dict[str, int]:
    balances: Dict[str, int] = {}
    for block in chain:
        for tx in block.transactions:
            if tx.sender_id not in (COINBASE_SENDER, GENESIS_SENDER):
                balances[tx.sender_id] = balances.get(tx.sender_id, 0) - tx.amount
            balances[tx.receiver_id] = balances.get(tx.receiver_id, 0) + tx.amount
    return balances


class DefaultBlockValidator(IBlockValidator):
    def __init__(
        self,
        proof_of_work: IProofOfWork,
        transaction_validator: ITransactionValidator,
        expected_difficulty: int,
        mining_reward: int,
        genesis_prefund_amount: int,
    ) -> None:
        self._proof_of_work = proof_of_work
        self._transaction_validator = transaction_validator
        self._expected_difficulty = expected_difficulty
        self._mining_reward = mining_reward
        self._genesis_prefund_amount = genesis_prefund_amount

    def validate(
        self,
        block: Block,
        previous_hash: str,
        *,
        previous_timestamp: Optional[datetime] = None,
    ) -> bool:
        return self.validate_with_balances(
            block, previous_hash, balances=None, previous_timestamp=previous_timestamp
        )

    def validate_with_balances(
        self,
        block: Block,
        previous_hash: str,
        balances: Optional[Dict[str, int]],
        previous_timestamp: Optional[datetime] = None,
    ) -> bool:
        if block.last_hash != previous_hash:
            return False
        if block.target != self._expected_difficulty and block.id != GENESIS_HEIGHT:
            return False
        if block.id != GENESIS_HEIGHT and not self._proof_of_work.verify(block):
            return False
        if (
            block.id != GENESIS_HEIGHT
            and previous_timestamp is not None
            and block.timestamp <= previous_timestamp
        ):
            return False

        if block.id == GENESIS_HEIGHT:
            return self._validate_genesis_block(block)

        return self._validate_mined_block(block, balances)

    def _validate_genesis_block(self, block: Block) -> bool:
        if block.id != GENESIS_HEIGHT:
            return False
        if block.last_hash != GENESIS_LAST_HASH:
            return False
        if block.target != 0:
            return False
        if block.nonce != GENESIS_NONCE:
            return False
        if block.timestamp.timestamp() != GENESIS_TIMESTAMP_EPOCH:
            return False
        tx_ids = [tx.id for tx in block.transactions]
        expected_hash = block_hash(
            GENESIS_LAST_HASH,
            GENESIS_TIMESTAMP_EPOCH,
            0,
            GENESIS_NONCE,
            tx_ids,
        )
        if block.hash != expected_hash:
            return False
        if not isinstance(self._transaction_validator, DefaultTransactionValidator):
            return False
        validator = self._transaction_validator
        for index, tx in enumerate(block.transactions):
            if not validator.validate_genesis_tx(
                tx, index, self._genesis_prefund_amount
            ):
                return False
        return True

    def _validate_mined_block(
        self, block: Block, balances: Optional[Dict[str, int]]
    ) -> bool:
        coinbase_txs = [
            tx for tx in block.transactions if tx.sender_id == COINBASE_SENDER
        ]
        if len(coinbase_txs) != 1:
            return False

        coinbase = coinbase_txs[0]
        if block.transactions[0].sender_id != COINBASE_SENDER:
            return False

        if not isinstance(self._transaction_validator, DefaultTransactionValidator):
            return False
        validator = self._transaction_validator
        if not validator.validate_coinbase(coinbase, block.id, self._mining_reward):
            return False

        if balances is not None:
            balances[coinbase.receiver_id] = (
                balances.get(coinbase.receiver_id, 0) + coinbase.amount
            )

        for tx in block.transactions[1:]:
            if tx.sender_id == COINBASE_SENDER:
                return False
            if balances is not None:
                available = balances.get(tx.sender_id, 0)
                if available < tx.amount:
                    return False
                if not validator.validate_crypto(tx):
                    return False
                balances[tx.sender_id] = available - tx.amount
                balances[tx.receiver_id] = balances.get(tx.receiver_id, 0) + tx.amount
            elif not validator.validate_crypto(tx):
                return False

        return True
