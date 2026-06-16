"""Adaptador: validación de transacciones (firma + reglas)."""

from typing import Optional

from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.application.interfaces.verifier import IVerifier
from main.domain.models.transaction import Transaction
from main.infrastructure.serialization.canonical import (
    coinbase_id,
    derive_sender_id,
    genesis_tx_id,
    transaction_firmable_bytes,
    transaction_id,
)

COINBASE_SENDER = "COINBASE"
GENESIS_SENDER = "GENESIS"


class DefaultTransactionValidator(ITransactionValidator):
    def __init__(
        self,
        verifier: IVerifier,
        transaction_repository: Optional[ITransactionRepository] = None,
    ) -> None:
        self._verifier = verifier
        self._transaction_repository = transaction_repository

    def validate(self, tx: Transaction) -> bool:
        if tx.sender_id in (COINBASE_SENDER, GENESIS_SENDER):
            return False

        if not tx.id or not tx.sender_id or not tx.receiver_id:
            return False
        if tx.sender_id == tx.receiver_id:
            return False
        if tx.amount <= 0:
            return False
        if derive_sender_id(tx.public_key) != tx.sender_id:
            return False

        firmable = transaction_firmable_bytes(tx.sender_id, tx.receiver_id, tx.amount)
        if not self._verifier.verify(firmable, tx.signature, tx.public_key):
            return False
        if transaction_id(firmable, tx.signature) != tx.id:
            return False

        if self._transaction_repository is not None:
            if self._transaction_repository.exists_in_mempool_or_chain(tx.id):
                return False
            available = self._transaction_repository.get_balance(tx.sender_id)
            for pending in self._transaction_repository.get_mempool():
                if pending.sender_id == tx.sender_id and pending.id != tx.id:
                    available -= pending.amount
            if available < tx.amount:
                return False

        return True

    def validate_crypto(self, tx: Transaction) -> bool:
        if tx.sender_id in (COINBASE_SENDER, GENESIS_SENDER):
            return self._validate_special(tx)

        if not tx.id or not tx.sender_id or not tx.receiver_id:
            return False
        if tx.sender_id == tx.receiver_id:
            return False
        if tx.amount <= 0:
            return False
        if derive_sender_id(tx.public_key) != tx.sender_id:
            return False

        firmable = transaction_firmable_bytes(tx.sender_id, tx.receiver_id, tx.amount)
        if not self._verifier.verify(firmable, tx.signature, tx.public_key):
            return False
        return transaction_id(firmable, tx.signature) == tx.id

    def _validate_special(self, tx: Transaction) -> bool:
        if tx.signature != b"" or tx.public_key != b"":
            return False
        if tx.amount <= 0:
            return False
        if tx.sender_id == GENESIS_SENDER:
            return True
        return tx.sender_id == COINBASE_SENDER

    def validate_coinbase(
        self, tx: Transaction, block_height: int, mining_reward: int
    ) -> bool:
        if tx.sender_id != COINBASE_SENDER:
            return False
        if tx.signature != b"" or tx.public_key != b"":
            return False
        if tx.amount != mining_reward:
            return False
        expected_id = coinbase_id(block_height, tx.receiver_id, mining_reward)
        return tx.id == expected_id

    def validate_genesis_tx(
        self, tx: Transaction, index: int, prefund_amount: int
    ) -> bool:
        if tx.sender_id != GENESIS_SENDER:
            return False
        if tx.signature != b"" or tx.public_key != b"":
            return False
        if tx.amount != prefund_amount:
            return False
        expected_id = genesis_tx_id(index, tx.receiver_id, prefund_amount)
        return tx.id == expected_id
