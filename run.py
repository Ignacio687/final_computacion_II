#!/usr/bin/env python3
"""Punto de entrada único. Selecciona nodo o billetera según subcomando.

    python run.py node    --node-id ... --bind-host 0.0.0.0 --tcp-port 8001 --http-port 9081 \\
                          --peers host:port,host:port --db-path ./node.db --difficulty 2 \\
                          --pow-workers 4 --min-tx-per-block 5 --block-interval-seconds 10 \\
                          --mining-reward 50 --mining-address ADDR --private-key-path priv.pem \\
                          --public-key-path pub.pem --shared-key BASE64KEY \\
                          --reconnect-delay-seconds 3 --genesis-seed SEED \\
                          --genesis-prefund-accounts 5 --genesis-prefund-amount 1000

    python run.py wallet  --node-url http://localhost:9081 --keys-dir ./keys \\
                          --genesis-seed SEED \\
                          [--generator --generator-users 10 --generator-interval-seconds 1.0]

Variables de entorno: --genesis-seed y --shared-key toman su valor de HASHCOIN_GENESIS_SEED
y HASHCOIN_SHARED_KEY respectivamente si no se pasan por CLI (útil en docker-compose).
"""
import argparse
import asyncio
import os
import sys


def _build_node_parser(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--node-id", type=str, required=True)
    sub.add_argument("--bind-host", type=str, default="0.0.0.0")
    sub.add_argument("--tcp-port", type=int, required=True)
    sub.add_argument("--http-port", type=int, required=True)
    sub.add_argument("--peers", type=str, default="", help="host:port,host:port")
    sub.add_argument("--db-path", type=str, required=True)
    sub.add_argument("--difficulty", type=int, required=True)
    sub.add_argument("--pow-workers", type=int, required=True)
    sub.add_argument("--min-tx-per-block", type=int, required=True)
    sub.add_argument("--block-interval-seconds", type=float, required=True)
    sub.add_argument("--mining-reward", type=int, required=True)
    sub.add_argument("--mining-address", type=str, required=True)
    sub.add_argument("--private-key-path", type=str, required=True)
    sub.add_argument("--public-key-path", type=str, required=True)
    sub.add_argument("--shared-key", type=str, default=os.environ.get("HASHCOIN_SHARED_KEY"),
                     help="clave simétrica precompartida en base64 (o env HASHCOIN_SHARED_KEY)")
    sub.add_argument("--reconnect-delay-seconds", type=float, default=3.0)
    sub.add_argument("--genesis-seed", type=str, default=os.environ.get("HASHCOIN_GENESIS_SEED"),
                     help="semilla del génesis (o env HASHCOIN_GENESIS_SEED)")
    sub.add_argument("--genesis-prefund-accounts", type=int, default=5)
    sub.add_argument("--genesis-prefund-amount", type=int, default=1000)


def _build_wallet_parser(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--node-url", type=str, required=True)
    sub.add_argument(
        "--fallback-node-url",
        type=str,
        default="",
        help="URL alternativa del nodo si la principal no responde (p. ej. node3)",
    )
    sub.add_argument("--keys-dir", type=str, required=True)
    sub.add_argument("--genesis-seed", type=str, default=os.environ.get("HASHCOIN_GENESIS_SEED"),
                     help="semilla del génesis (o env HASHCOIN_GENESIS_SEED)")
    sub.add_argument("--generator", action="store_true")
    sub.add_argument("--generator-users", type=int, default=0)
    sub.add_argument("--generator-interval-seconds", type=float, default=1.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="HashCoin: nodo o billetera")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _build_node_parser(subparsers.add_parser("node"))
    _build_wallet_parser(subparsers.add_parser("wallet"))
    args = parser.parse_args()

    if args.command == "node":
        from main.bootstrap.shared_key import require_shared_key_b64
        from main.config.node_config import NodeConfig
        from main.domain.models.node_info import NodeInfo
        from main.bootstrap.node_bootstrap import create_and_run_node

        shared_key = require_shared_key_b64(args.shared_key)

        peers = []
        if args.peers:
            for part in args.peers.split(","):
                part = part.strip()
                if ":" in part:
                    host, port_str = part.rsplit(":", 1)
                    peers.append(NodeInfo(host=host.strip(), port=int(port_str)))
        config = NodeConfig(
            node_id=args.node_id,
            bind_host=args.bind_host,
            tcp_port=args.tcp_port,
            http_port=args.http_port,
            peers=peers,
            db_path=args.db_path,
            difficulty=args.difficulty,
            pow_workers=args.pow_workers,
            min_transactions_per_block=args.min_tx_per_block,
            block_interval_seconds=args.block_interval_seconds,
            mining_reward=args.mining_reward,
            mining_address=args.mining_address,
            private_key_path=args.private_key_path,
            public_key_path=args.public_key_path,
            shared_key=shared_key,
            reconnect_delay_seconds=args.reconnect_delay_seconds,
            genesis_seed=args.genesis_seed,
            genesis_prefund_accounts=args.genesis_prefund_accounts,
            genesis_prefund_amount=args.genesis_prefund_amount,
        )
        asyncio.run(create_and_run_node(config))
        return 0

    if args.command == "wallet":
        from main.config.wallet_config import WalletConfig
        from main.bootstrap.wallet_bootstrap import run_wallet

        fallback_urls = tuple(
            part.strip()
            for part in args.fallback_node_url.split(",")
            if part.strip()
        )
        config = WalletConfig(
            node_url=args.node_url,
            fallback_node_urls=fallback_urls,
            keys_dir=args.keys_dir,
            generator_mode=args.generator,
            generator_users=args.generator_users,
            generator_interval_seconds=args.generator_interval_seconds,
            genesis_seed=args.genesis_seed,
        )
        return run_wallet(config)

    return 1


if __name__ == "__main__":
    sys.exit(main())
