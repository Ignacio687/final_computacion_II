"""Tests HTTP: handlers y servidor (doc/protocolo.md §10)."""

import asyncio
import dataclasses
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from main.controller.http_handlers import HTTPHandlers
from main.infrastructure.crypto.verifier import CryptographyVerifier
from main.infrastructure.genesis.seed_genesis_provider import SeedGenesisProvider
from main.infrastructure.http.http_server import HTTPServer
from main.infrastructure.http.limits import MAX_POST_BODY_BYTES
from main.infrastructure.persistence.sqlite.blockchain_repository import (
    SQLiteBlockchainRepository,
)
from main.infrastructure.persistence.sqlite.transaction_repository import (
    SQLiteTransactionRepository,
)
from main.infrastructure.validation.transaction_validator import DefaultTransactionValidator
from main.repository.dto.mappers import transaction_to_dto
from main.service.transaction_submit_service import TransactionSubmitService
from main.service.wallet_query_service import WalletQueryService
from main.wallet.key_store import KeyStore
from main.wallet.tx_builder import build_signed_transaction
from tests.node_test_helpers import (
    GENESIS_PREFUND_ACCOUNTS,
    GENESIS_PREFUND_AMOUNT,
    GENESIS_SEED,
    free_port,
    tx_repo,
)


async def _raw_http(
    port: int,
    method: str,
    target: str,
    *,
    body: bytes = b"",
    content_length: int | None = None,
) -> tuple[int, dict]:
    """Envía una petición HTTP/1.1 mínima y devuelve (status, body_json)."""
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        length = content_length if content_length is not None else len(body)
        header_lines = [
            f"{method} {target} HTTP/1.1",
            f"Host: 127.0.0.1:{port}",
            "Connection: close",
        ]
        if method == "POST":
            header_lines.append("Content-Type: application/json")
            header_lines.append(f"Content-Length: {length}")
        request = "\r\n".join(header_lines).encode("ascii") + b"\r\n\r\n" + body
        writer.write(request)
        await writer.drain()

        status_line = await reader.readline()
        status = int(status_line.decode("ascii").split()[1])
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b""):
                break
        raw_body = await reader.read()
        return status, json.loads(raw_body.decode("utf-8")) if raw_body else {}
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


@pytest.fixture
async def http_server(tmp_path):
    """Servidor HTTP con persistencia SQLite y génesis cargado."""
    port = free_port()
    db_path = str(tmp_path / "http_node.db")
    blockchain_repo = SQLiteBlockchainRepository(db_path)
    transaction_repo = SQLiteTransactionRepository(db_path)
    genesis = SeedGenesisProvider(
        GENESIS_SEED, GENESIS_PREFUND_ACCOUNTS, GENESIS_PREFUND_AMOUNT
    ).get_genesis_block()
    blockchain_repo.append_block(genesis)

    verifier = CryptographyVerifier()
    transaction_validator = DefaultTransactionValidator(verifier, transaction_repo)
    message_sender = MagicMock()
    message_sender.connected_count = MagicMock(return_value=0)
    message_sender.broadcast = AsyncMock()

    chain_lock = asyncio.Lock()
    wallet_query = WalletQueryService(
        transaction_repo,
        blockchain_repo,
        message_sender,
        "test-node",
        difficulty=1,
    )
    transaction_submit = TransactionSubmitService(
        transaction_repo,
        transaction_validator,
        message_sender,
        chain_lock,
    )
    handlers = HTTPHandlers(wallet_query, transaction_submit)
    server = HTTPServer("127.0.0.1", port, handlers)
    await server.start()
    try:
        yield port, db_path
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_post_tx_invalid_json_returns_400(http_server):
    port, _ = http_server
    status, body = await _raw_http(port, "POST", "/tx", body=b"not-json{")
    assert status == 400
    assert body == {
        "accepted": False,
        "tx_id": None,
        "error": "JSON inválido",
    }


@pytest.mark.asyncio
async def test_post_tx_rejected_returns_400_section_10_format(http_server):
    port, _ = http_server
    status, body = await _raw_http(
        port,
        "POST",
        "/tx",
        body=json.dumps({"id": "x", "amount": -1}).encode("utf-8"),
    )
    assert status == 400
    assert body["accepted"] is False
    assert body["tx_id"] is None
    assert isinstance(body["error"], str) and body["error"]


@pytest.mark.asyncio
async def test_unknown_route_returns_404(http_server):
    port, _ = http_server
    status, body = await _raw_http(port, "GET", "/no-such-route")
    assert status == 404
    assert body == {"error": "not found"}


@pytest.mark.asyncio
async def test_balance_without_address_returns_400(http_server):
    port, _ = http_server
    status, body = await _raw_http(port, "GET", "/balance")
    assert status == 400
    assert body == {"error": "address required"}


@pytest.mark.asyncio
async def test_post_duplicate_tx_does_not_duplicate_mempool(http_server):
    port, db_path = http_server
    accounts = KeyStore.derive_genesis_accounts(GENESIS_SEED, GENESIS_PREFUND_ACCOUNTS)
    tx = build_signed_transaction(accounts[0], accounts[1].id, amount=10)
    payload = json.dumps(dataclasses.asdict(transaction_to_dto(tx))).encode("utf-8")

    status1, body1 = await _raw_http(port, "POST", "/tx", body=payload)
    assert status1 == 200
    assert body1["accepted"] is True

    status2, body2 = await _raw_http(port, "POST", "/tx", body=payload)
    assert status2 == 400
    assert body2["accepted"] is False
    assert body2["tx_id"] is None

    mempool = tx_repo(db_path).get_mempool()
    assert sum(1 for item in mempool if item.id == tx.id) == 1


@pytest.mark.asyncio
async def test_post_body_over_64kib_returns_413(http_server):
    port, _ = http_server
    status, body = await _raw_http(
        port,
        "POST",
        "/tx",
        content_length=MAX_POST_BODY_BYTES + 1,
    )
    assert status == 413
    assert body == {"error": "payload too large"}
