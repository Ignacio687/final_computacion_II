#!/usr/bin/env python3
"""Punto de entrada único. Selecciona nodo o billetera según subcomando.

    python run.py node    --node-id ... --bind-host 0.0.0.0 --tcp-port 8001 --http-port 9081 \\
                          --peers host:port,host:port --db-path ./node.db --difficulty 2 \\
                          --pow-workers 4 --min-tx-per-block 5 --block-interval-seconds 10 \\
                          --mining-reward 50 --mining-address ADDR --private-key-path priv.pem \\
                          --public-key-path pub.pem --ping-interval-seconds 5 \\
                          --pong-timeout-seconds 15 --reconnect-initial-seconds 1 \\
                          --reconnect-max-seconds 30 --genesis-seed SEED

    python run.py wallet  --node-url http://localhost:9081 --keys-dir ./keys \\
                          [--generator --generator-users 10 --generator-interval-seconds 1.0]
"""
import argparse
import asyncio
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
    sub.add_argument("--ping-interval-seconds", type=float, required=True)
    sub.add_argument("--pong-timeout-seconds", type=float, required=True)
    sub.add_argument("--reconnect-initial-seconds", type=float, required=True)
    sub.add_argument("--reconnect-max-seconds", type=float, required=True)
    sub.add_argument("--genesis-seed", type=str, required=True)


def _build_wallet_parser(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--node-url", type=str, required=True)
    sub.add_argument("--keys-dir", type=str, required=True)
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
        from main.config.node_config import NodeConfig
        from main.domain.models.node_info import NodeInfo
        from main.bootstrap.node_bootstrap import create_and_run_node

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
            ping_interval_seconds=args.ping_interval_seconds,
            pong_timeout_seconds=args.pong_timeout_seconds,
            reconnect_initial_seconds=args.reconnect_initial_seconds,
            reconnect_max_seconds=args.reconnect_max_seconds,
            genesis_seed=args.genesis_seed,
        )
        asyncio.run(create_and_run_node(config))
        return 0

    if args.command == "wallet":
        from main.config.wallet_config import WalletConfig
        from main.bootstrap.wallet_bootstrap import run_wallet

        config = WalletConfig(
            node_url=args.node_url,
            keys_dir=args.keys_dir,
            generator_mode=args.generator,
            generator_users=args.generator_users,
            generator_interval_seconds=args.generator_interval_seconds,
        )
        return run_wallet(config)

    return 1


if __name__ == "__main__":
    sys.exit(main())
