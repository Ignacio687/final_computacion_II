"""Handlers HTTP: GET /balance, GET /transactions, GET /status, POST /tx."""

import dataclasses
import json

from main.application.interfaces.transaction_submit import ITransactionSubmit
from main.application.interfaces.wallet_query import IWalletQuery
from main.repository.dto.mappers import transaction_from_dto, transaction_to_dto
from main.repository.dto.transaction_dto import TransactionDTO


class HTTPHandlers:
    """Mapeo ruta -> handler."""

    def __init__(
        self, wallet_query: IWalletQuery, transaction_submit: ITransactionSubmit
    ) -> None:
        self._wallet_query = wallet_query
        self._transaction_submit = transaction_submit

    async def handle_get_balance(self, address: str) -> dict:
        balance = self._wallet_query.get_balance(address)
        return {"address": address, "balance": balance}

    async def handle_get_transactions(
        self, address: str | None, limit: int
    ) -> list:
        transactions = self._wallet_query.get_transactions(address, limit)
        return [dataclasses.asdict(transaction_to_dto(tx)) for tx in transactions]

    async def handle_get_status(self) -> dict:
        return self._wallet_query.get_status()

    async def handle_post_tx(self, body: bytes) -> tuple[int, dict]:
        try:
            data = json.loads(body.decode("utf-8"))
            dto = TransactionDTO(**data)
            tx = transaction_from_dto(dto)
        except (json.JSONDecodeError, TypeError, ValueError):
            return 400, {
                "accepted": False,
                "tx_id": None,
                "error": "JSON inválido",
            }

        accepted = await self._transaction_submit.submit_transaction(tx)
        if accepted:
            return 200, {
                "accepted": True,
                "tx_id": tx.id,
                "error": None,
            }
        return 400, {
            "accepted": False,
            "tx_id": None,
            "error": "transacción rechazada",
        }
