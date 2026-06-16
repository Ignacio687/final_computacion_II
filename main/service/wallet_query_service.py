"""Implementación de IWalletQuery."""

from typing import List

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.wallet_query import IWalletQuery
from main.domain.models.transaction import Transaction


class WalletQueryService(IWalletQuery):
    """Compone los datos para los handlers HTTP GET."""

    def __init__(
        self,
        transaction_repository: ITransactionRepository,
        blockchain_repository: IBlockchainRepository,
        message_sender: IMessageSender,
        node_id: str,
        difficulty: int,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._blockchain_repository = blockchain_repository
        self._message_sender = message_sender
        self._node_id = node_id
        self._difficulty = difficulty

    def get_balance(self, address: str) -> int:
        return self._transaction_repository.get_balance(address)

    def get_transactions(self, address: str | None, limit: int) -> List[Transaction]:
        if address is not None:
            return self._transaction_repository.get_transactions_for_address(
                address, limit
            )
        return self._transaction_repository.get_recent_transactions(limit)

    def get_status(self) -> dict:
        return {
            "node_id": self._node_id,
            "height": self._blockchain_repository.get_height(),
            "difficulty": self._difficulty,
            "mempool_size": len(self._transaction_repository.get_mempool()),
            "peers_connected": self._message_sender.connected_count(),
        }
