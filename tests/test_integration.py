"""Tests de integración 2.1 y 2.2 (doc/plan_pruebas.md)."""

import asyncio
from pathlib import Path

import pytest

from main.domain.models.node_info import NodeInfo
from main.wallet.key_store import KeyStore
from main.wallet.tx_builder import build_signed_transaction
from tests.node_test_helpers import (
    GENESIS_PREFUND_ACCOUNTS,
    GENESIS_PREFUND_AMOUNT,
    GENESIS_SEED,
    MINING_REWARD,
    NodeCluster,
    async_http_get_balance,
    async_http_post_tx,
    build_node_config,
    chain_repo,
    free_port,
    tx_repo,
    wait_for_peers,
    wait_until,
)


@pytest.fixture
def integration_tmp(tmp_path: Path) -> Path:
    return tmp_path


@pytest.mark.asyncio
async def test_transaction_propagation_between_two_nodes(integration_tmp: Path) -> None:
    """2.1: POST /tx en A → mempool de B sin duplicar."""
    tcp_a, http_a = free_port(), free_port()
    tcp_b, http_b = free_port(), free_port()
    config_a, db_a, _ = build_node_config(
        integration_tmp,
        "node-a",
        tcp_a,
        http_a,
        [NodeInfo(host="127.0.0.1", port=tcp_b)],
        min_transactions_per_block=5,
    )
    config_b, db_b, _ = build_node_config(
        integration_tmp,
        "node-b",
        tcp_b,
        http_b,
        [NodeInfo(host="127.0.0.1", port=tcp_a)],
        min_transactions_per_block=5,
    )

    cluster = NodeCluster()
    await cluster.start(config_a, config_b)
    try:
        await wait_for_peers(http_a)
        await wait_for_peers(http_b)

        accounts = KeyStore.derive_genesis_accounts(
            GENESIS_SEED, GENESIS_PREFUND_ACCOUNTS
        )
        sender, receiver = accounts[0], accounts[1]
        tx = build_signed_transaction(sender, receiver.id, amount=10)

        status, body = await async_http_post_tx(http_a, tx)
        assert status == 200
        assert body["accepted"] is True
        assert body["tx_id"] == tx.id

        repo_b = tx_repo(db_b)

        def tx_in_b_mempool() -> bool:
            return any(item.id == tx.id for item in repo_b.get_mempool())

        await wait_until(tx_in_b_mempool, timeout=10.0)
        assert sum(1 for item in repo_b.get_mempool() if item.id == tx.id) == 1
    finally:
        await cluster.stop()


@pytest.mark.asyncio
async def test_mining_and_block_propagation_between_two_nodes(
    integration_tmp: Path,
) -> None:
    """2.2: minado en A → bloque y balances confirmados en B."""
    tcp_a, http_a = free_port(), free_port()
    tcp_b, http_b = free_port(), free_port()
    config_a, db_a, mining_a = build_node_config(
        integration_tmp,
        "node-a",
        tcp_a,
        http_a,
        [NodeInfo(host="127.0.0.1", port=tcp_b)],
        min_transactions_per_block=1,
        block_interval_seconds=3600.0,
    )
    config_b, db_b, _ = build_node_config(
        integration_tmp,
        "node-b",
        tcp_b,
        http_b,
        [NodeInfo(host="127.0.0.1", port=tcp_a)],
        min_transactions_per_block=99,
        block_interval_seconds=3600.0,
    )

    cluster = NodeCluster()
    await cluster.start(config_a, config_b)
    try:
        await wait_for_peers(http_a)
        await wait_for_peers(http_b)

        accounts = KeyStore.derive_genesis_accounts(
            GENESIS_SEED, GENESIS_PREFUND_ACCOUNTS
        )
        sender, receiver = accounts[0], accounts[1]
        tx = build_signed_transaction(sender, receiver.id, amount=10)

        status, body = await async_http_post_tx(http_a, tx)
        assert status == 200 and body["accepted"] is True

        repo_a = chain_repo(db_a)
        repo_b = chain_repo(db_b)

        def tx_confirmed_and_chains_synced() -> bool:
            if repo_a.get_height() < 2 or repo_b.get_height() < 2:
                return False
            if repo_a.get_last_block().hash != repo_b.get_last_block().hash:
                return False
            if repo_a.get_height() != repo_b.get_height():
                return False
            return tx.id not in {item.id for item in tx_repo(db_b).get_mempool()}

        await wait_until(tx_confirmed_and_chains_synced, timeout=25.0)

        expected_receiver = GENESIS_PREFUND_AMOUNT + 10
        expected_sender = GENESIS_PREFUND_AMOUNT - 10

        for http_port in (http_a, http_b):
            assert await async_http_get_balance(http_port, receiver.id) == expected_receiver
            assert await async_http_get_balance(http_port, sender.id) == expected_sender
            miner_balance = await async_http_get_balance(http_port, mining_a)
            assert miner_balance >= MINING_REWARD
        assert await async_http_get_balance(http_a, mining_a) == await async_http_get_balance(
            http_b, mining_a
        )
    finally:
        await cluster.stop()
