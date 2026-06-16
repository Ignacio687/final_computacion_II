"""Utilidades para tests de integración con nodos en proceso."""

import asyncio
import base64
import dataclasses
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.bootstrap.node_bootstrap import create_and_run_node
from main.config.node_config import NodeConfig
from main.domain.models.node_info import NodeInfo
from main.domain.models.transaction import Transaction
from main.infrastructure.persistence.sqlite.blockchain_repository import (
    SQLiteBlockchainRepository,
)
from main.infrastructure.persistence.sqlite.transaction_repository import (
    SQLiteTransactionRepository,
)
from main.infrastructure.serialization.canonical import derive_sender_id
from main.repository.dto.mappers import transaction_to_dto

GENESIS_SEED = "test-seed"
SHARED_KEY_B64 = base64.b64encode(b"\x00" * 32).decode("ascii")
DIFFICULTY = 1
MINING_REWARD = 50
GENESIS_PREFUND_ACCOUNTS = 3
GENESIS_PREFUND_AMOUNT = 1000


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def write_node_keys(base_dir: Path, name: str) -> tuple[str, str, str]:
    """Genera PEM del nodo y devuelve (priv_path, pub_path, mining_address)."""
    private_key = Ed25519PrivateKey.generate()
    node_dir = base_dir / name
    node_dir.mkdir(parents=True, exist_ok=True)
    private_path = node_dir / "priv.pem"
    public_path = node_dir / "pub.pem"
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return str(private_path), str(public_path), derive_sender_id(public_der)


def build_node_config(
    tmp_path: Path,
    node_id: str,
    tcp_port: int,
    http_port: int,
    peers: list[NodeInfo],
    *,
    min_transactions_per_block: int = 5,
    block_interval_seconds: float = 10.0,
) -> tuple[NodeConfig, str, str]:
    priv_path, pub_path, mining_address = write_node_keys(tmp_path, node_id)
    db_path = str(tmp_path / f"{node_id}.db")
    config = NodeConfig(
        node_id=node_id,
        bind_host="127.0.0.1",
        tcp_port=tcp_port,
        http_port=http_port,
        peers=peers,
        db_path=db_path,
        difficulty=DIFFICULTY,
        pow_workers=2,
        min_transactions_per_block=min_transactions_per_block,
        block_interval_seconds=block_interval_seconds,
        mining_reward=MINING_REWARD,
        mining_address=mining_address,
        private_key_path=priv_path,
        public_key_path=pub_path,
        shared_key=SHARED_KEY_B64,
        reconnect_delay_seconds=0.5,
        genesis_seed=GENESIS_SEED,
        genesis_prefund_accounts=GENESIS_PREFUND_ACCOUNTS,
        genesis_prefund_amount=GENESIS_PREFUND_AMOUNT,
    )
    return config, db_path, mining_address


def http_get_status(http_port: int) -> dict:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{http_port}/status", timeout=2
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get_balance(http_port: int, address: str) -> int:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{http_port}/balance?address={address}", timeout=2
    ) as response:
        return json.loads(response.read().decode("utf-8"))["balance"]


def http_post_tx(http_port: int, tx: Transaction) -> tuple[int, dict]:
    body = json.dumps(dataclasses.asdict(transaction_to_dto(tx))).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{http_port}/tx",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


async def wait_until(predicate, timeout: float = 10.0, interval: float = 0.1) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(interval)
    raise TimeoutError("Condición no cumplida dentro del tiempo límite")


async def async_http_get_status(http_port: int) -> dict:
    return await asyncio.to_thread(http_get_status, http_port)


async def async_http_get_balance(http_port: int, address: str) -> int:
    return await asyncio.to_thread(http_get_balance, http_port, address)


async def async_http_post_tx(http_port: int, tx: Transaction) -> tuple[int, dict]:
    return await asyncio.to_thread(http_post_tx, http_port, tx)


async def wait_for_peers(http_port: int, min_peers: int = 1, timeout: float = 10.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        try:
            status = await async_http_get_status(http_port)
            if status["peers_connected"] >= min_peers:
                return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        await asyncio.sleep(0.1)
    raise TimeoutError(f"Nodo en :{http_port} no alcanzó {min_peers} peer(s)")


class NodeCluster:
    """Arranca nodos en tareas asyncio y los detiene al salir del contexto."""

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task] = []

    async def start(self, *configs: NodeConfig) -> None:
        for config in configs:
            self._tasks.append(asyncio.create_task(create_and_run_node(config)))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()


def tx_repo(db_path: str) -> SQLiteTransactionRepository:
    return SQLiteTransactionRepository(db_path)


def chain_repo(db_path: str) -> SQLiteBlockchainRepository:
    return SQLiteBlockchainRepository(db_path)
