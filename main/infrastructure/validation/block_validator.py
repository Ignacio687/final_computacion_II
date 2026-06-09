"""Adaptador: validación de bloques (hash, PoW, transacciones). Ver doc/protocolo.md §5.3."""

from typing import Dict, Optional

from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.proof_of_work import IProofOfWork
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.domain.models.block import Block
from main.infrastructure.validation.transaction_validator import (
    COINBASE_SENDER,
    DefaultTransactionValidator,
)

GENESIS_HEIGHT = 0


class DefaultBlockValidator(IBlockValidator):
    """Implementación de IBlockValidator.

    Dependencias inyectadas para poder validar el bloque completo:
    - proof_of_work: recálculo de hash y verificación del PoW.
    - transaction_validator: validez de cada tx no-coinbase.
    - expected_difficulty: target esperado de la red (`block.target` debe coincidir).
    - mining_reward: amount esperado de la única tx coinbase del bloque.
    """

    def __init__(
        self,
        proof_of_work: IProofOfWork,
        transaction_validator: ITransactionValidator,
        expected_difficulty: int,
        mining_reward: int,
    ) -> None:
        self._proof_of_work = proof_of_work
        self._transaction_validator = transaction_validator
        self._expected_difficulty = expected_difficulty
        self._mining_reward = mining_reward

    def validate(self, block: Block, previous_hash: str) -> bool:
        return self.validate_with_balances(block, previous_hash, balances=None)

    def validate_with_balances(
        self,
        block: Block,
        previous_hash: str,
        balances: Optional[Dict[str, int]],
    ) -> bool:
        if block.last_hash != previous_hash:
            return False
        if block.target != self._expected_difficulty and block.id != GENESIS_HEIGHT:
            return False
        if block.id != GENESIS_HEIGHT and not self._proof_of_work.verify(block):
            return False

        if block.id == GENESIS_HEIGHT:
            return self._validate_genesis_block(block)

        return self._validate_mined_block(block, balances)

    def _validate_genesis_block(self, block: Block) -> bool:
        if block.target != 0:
            return False
        if not isinstance(self._transaction_validator, DefaultTransactionValidator):
            return False
        validator = self._transaction_validator
        for index, tx in enumerate(block.transactions):
            if not validator.validate_genesis_tx(tx, index, tx.amount):
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
            elif not validator.validate(tx):
                return False

        return True
