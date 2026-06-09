"""Tests de integración: sincronización de cadena (GET_CHAIN / CHAIN_RESPONSE)."""

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
    wait_for_peers,
    wait_until,
)


@pytest.fixture
def sync_tmp(tmp_path: Path) -> Path:
    return tmp_path


@pytest.mark.asyncio
async def test_short_chain_node_replaces_via_get_chain(sync_tmp: Path) -> None:
    """Nodo B (cadena corta) sincroniza cadena más larga de A vía GET_CHAIN/CHAIN_RESPONSE."""
    tcp_a, http_a = free_port(), free_port()
    tcp_b, http_b = free_port(), free_port()

    config_a, db_a, mining_a = build_node_config(
        sync_tmp,
        "node-a",
        tcp_a,
        http_a,
        [NodeInfo(host="127.0.0.1", port=tcp_b)],
        min_transactions_per_block=1,
        block_interval_seconds=3600.0,
    )
    config_b, db_b, _ = build_node_config(
        sync_tmp,
        "node-b",
        tcp_b,
        http_b,
        [NodeInfo(host="127.0.0.1", port=tcp_a)],
        min_transactions_per_block=99,
        block_interval_seconds=3600.0,
    )

    accounts = KeyStore.derive_genesis_accounts(GENESIS_SEED, GENESIS_PREFUND_ACCOUNTS)
    sender, receiver = accounts[0], accounts[1]

    cluster = NodeCluster()
    await cluster.start(config_a)
    try:
        repo_a = chain_repo(db_a)

        def node_a_ready() -> bool:
            try:
                return repo_a.get_height() >= 0
            except Exception:
                return False

        await wait_until(node_a_ready, timeout=15.0)
        height_before_mining = repo_a.get_height()

        for amount in (5, 7):
            tx = build_signed_transaction(sender, receiver.id, amount=amount)
            status, body = await async_http_post_tx(http_a, tx)
            assert status == 200 and body["accepted"] is True

            def block_mined(current_height: int = height_before_mining) -> bool:
                return repo_a.get_height() > current_height

            await wait_until(block_mined, timeout=25.0)
            height_before_mining = repo_a.get_height()

        target_height = repo_a.get_height()
        await cluster.start(config_b)
        await wait_for_peers(http_b, min_peers=1, timeout=15.0)

        repo_b = chain_repo(db_b)
        assert repo_b.get_height() < target_height

        tx_trigger = build_signed_transaction(sender, receiver.id, amount=3)
        status, body = await async_http_post_tx(http_a, tx_trigger)
        assert status == 200 and body["accepted"] is True

        def chains_synced() -> bool:
            return (
                repo_b.get_height() == repo_a.get_height()
                and repo_a.get_last_block().hash == repo_b.get_last_block().hash
            )

        await wait_until(chains_synced, timeout=30.0)

        final_height = repo_a.get_height()
        assert final_height > target_height

        expected_sender = GENESIS_PREFUND_AMOUNT - 5 - 7 - 3
        expected_receiver = GENESIS_PREFUND_AMOUNT + 5 + 7 + 3
        expected_miner = MINING_REWARD * final_height

        for http_port in (http_a, http_b):
            assert await async_http_get_balance(http_port, receiver.id) == expected_receiver
            assert await async_http_get_balance(http_port, sender.id) == expected_sender
            assert await async_http_get_balance(http_port, mining_a) == expected_miner
    finally:
        await cluster.stop()
