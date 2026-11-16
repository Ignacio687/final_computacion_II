#!/usr/bin/env python3
"""CLI interactiva de HashCoin para desarrollo local.

Delega en run.py sin duplicar el bootstrap del nodo ni de la billetera.

Uso rápido:
    python hashcoin.py node start
    python hashcoin.py wallet
    python hashcoin.py network
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.infrastructure.serialization.canonical import derive_sender_id

DEFAULT_GENESIS_SEED = "hashcoin-docker-seed"
DEFAULT_SHARED_KEY = "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
DEFAULT_DATA_DIR = Path("./data")

NODE_HELP = """\
Subcomandos del nodo HashCoin
=============================

  start   Levanta un nodo con defaults de desarrollo local.
  help    Muestra esta ayuda detallada.

Parámetros expuestos en ``node start`` (cátedra: PoW, núcleos, mempool):
  --node-id, --bind-host, --tcp-port, --http-port, --peers
  --difficulty          ceros hex iniciales del hash (target PoW)
  --pow-workers         procesos del ProcessPoolExecutor para minado
  --min-tx-per-block    mínimo de transacciones para armar un bloque
  --block-interval-seconds
  --mining-reward
  --db-path             SQLite del nodo (auto: ./data/<node-id>/node.db)
  --data-dir            directorio base si --db-path no se indica
  --log-level           nivel de logs del nodo (DEBUG/INFO/WARNING)

Secretos compartidos (misma red):
  HASHCOIN_GENESIS_SEED   semilla del bloque génesis
  HASHCOIN_SHARED_KEY     clave simétrica precompartida en base64

Defaults de laboratorio (si no hay env):
  genesis-seed = hashcoin-docker-seed
  shared-key   = 16 bytes 0x01 en base64 (ver .env.example)

Las claves Ed25519 del nodo se generan en ./data/<node-id>/keys/ si no existen.
"""

WALLET_HELP = """\
Billetera HashCoin (consola interactiva)
=======================================

Conecta al HTTP de un nodo y permite consultar saldos, enviar transacciones
o correr el generador de tráfico de prueba.

  --node-url              URL HTTP del nodo (default: http://127.0.0.1:9081)
  --fallback-node-url     URL alternativa si la principal no responde
  --keys-dir              directorio de claves de usuario (default: ./wallet-keys)
  --generator             modo generador de transacciones de prueba
  --generator-users       cantidad de cuentas pre-fondeadas a usar
  --generator-interval-seconds  intervalo entre envíos del generador
  --genesis-seed          semilla del génesis (o env HASHCOIN_GENESIS_SEED)
"""

NETWORK_HELP = """\
Red de ejemplo (dos nodos en local)
===================================

Terminal 1 — nodo 1:
  python hashcoin.py node start --node-id node1 --tcp-port 8001 --http-port 9081

Terminal 2 — nodo 2 con peer al nodo 1:
  python hashcoin.py node start --node-id node2 --tcp-port 8002 --http-port 9082 \\
    --peers 127.0.0.1:8001

Terminal 3 — billetera contra el nodo 1:
  python hashcoin.py wallet --node-url http://127.0.0.1:9081

Equivalente con run.py:
  python run.py node --node-id node1 ...   # mismos flags que hashcoin traduce

Verificar estado:
  curl http://127.0.0.1:9081/status
"""


def _ensure_node_keys(keys_dir: Path) -> tuple[str, str, str]:
    """Genera o reutiliza claves del nodo; devuelve (priv, pub, mining_address)."""
    keys_dir.mkdir(parents=True, exist_ok=True)
    private_path = keys_dir / "priv.pem"
    public_path = keys_dir / "pub.pem"
    address_path = keys_dir / "mining_address.txt"

    if private_path.is_file() and public_path.is_file() and address_path.is_file():
        return (
            str(private_path),
            str(public_path),
            address_path.read_text(encoding="utf-8").strip(),
        )

    private_key = Ed25519PrivateKey.generate()
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    mining_address = derive_sender_id(public_der)
    address_path.write_text(mining_address, encoding="utf-8")
    return str(private_path), str(public_path), mining_address


def _resolve_node_paths(args: argparse.Namespace) -> tuple[str, str, str, str]:
    data_root = Path(args.data_dir)
    node_dir = data_root / args.node_id
    keys_dir = node_dir / "keys"
    db_path = args.db_path or str(node_dir / "node.db")
    private_path, public_path, mining_address = _ensure_node_keys(keys_dir)
    node_dir.mkdir(parents=True, exist_ok=True)
    return db_path, private_path, public_path, mining_address


def _node_start_argv(args: argparse.Namespace) -> list[str]:
    db_path, private_path, public_path, mining_address = _resolve_node_paths(args)
    genesis_seed = args.genesis_seed or os.environ.get(
        "HASHCOIN_GENESIS_SEED", DEFAULT_GENESIS_SEED
    )
    shared_key = args.shared_key or os.environ.get(
        "HASHCOIN_SHARED_KEY", DEFAULT_SHARED_KEY
    )
    argv = [
        "run.py",
        "node",
        "--node-id",
        args.node_id,
        "--bind-host",
        args.bind_host,
        "--tcp-port",
        str(args.tcp_port),
        "--http-port",
        str(args.http_port),
        "--peers",
        args.peers,
        "--db-path",
        db_path,
        "--difficulty",
        str(args.difficulty),
        "--pow-workers",
        str(args.pow_workers),
        "--min-tx-per-block",
        str(args.min_tx_per_block),
        "--block-interval-seconds",
        str(args.block_interval_seconds),
        "--mining-reward",
        str(args.mining_reward),
        "--mining-address",
        mining_address,
        "--private-key-path",
        private_path,
        "--public-key-path",
        public_path,
        "--shared-key",
        shared_key,
        "--genesis-seed",
        genesis_seed,
        "--genesis-prefund-accounts",
        str(args.genesis_prefund_accounts),
        "--genesis-prefund-amount",
        str(args.genesis_prefund_amount),
        "--reconnect-delay-seconds",
        str(args.reconnect_delay_seconds),
    ]
    if args.verbose:
        argv.append("--verbose")
    else:
        argv.extend(["--log-level", args.log_level])
    return argv


def _wallet_argv(args: argparse.Namespace) -> list[str]:
    genesis_seed = args.genesis_seed or os.environ.get(
        "HASHCOIN_GENESIS_SEED", DEFAULT_GENESIS_SEED
    )
    argv = [
        "run.py",
        "wallet",
        "--node-url",
        args.node_url,
        "--fallback-node-url",
        args.fallback_node_url,
        "--keys-dir",
        args.keys_dir,
        "--genesis-seed",
        genesis_seed,
    ]
    if args.generator:
        argv.append("--generator")
        argv.extend(
            [
                "--generator-users",
                str(args.generator_users),
                "--generator-interval-seconds",
                str(args.generator_interval_seconds),
            ]
        )
    return argv


def _add_node_start_parser(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--node-id",
        type=str,
        default="node1",
        help="identificador del nodo (default: node1)",
    )
    sub.add_argument(
        "--bind-host",
        type=str,
        default="auto",
        help="escucha: auto (sockets IPv4+IPv6 nativos dedicados), 0.0.0.0, ::, 127.0.0.1, ::1 (default: auto)",
    )
    sub.add_argument(
        "--tcp-port",
        type=int,
        default=8001,
        help="puerto P2P entre nodos (default: 8001)",
    )
    sub.add_argument(
        "--http-port",
        type=int,
        default=9081,
        help="puerto HTTP para billetera (default: 9081)",
    )
    sub.add_argument(
        "--peers",
        type=str,
        default="",
        help="lista host:puerto_tcp separada por comas (default: ninguno)",
    )
    sub.add_argument(
        "--data-dir",
        type=str,
        default=str(DEFAULT_DATA_DIR),
        help="directorio base de datos y claves (default: ./data)",
    )
    sub.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="ruta SQLite; si se omite: <data-dir>/<node-id>/node.db",
    )
    sub.add_argument(
        "--difficulty",
        type=int,
        default=2,
        help="ceros hex iniciales del PoW (default: 2)",
    )
    sub.add_argument(
        "--pow-workers",
        type=int,
        default=max(1, (os.cpu_count() or 2) // 2),
        help="procesos del pool de minado (default: mitad de CPUs)",
    )
    sub.add_argument(
        "--min-tx-per-block",
        type=int,
        default=3,
        help="mínimo de tx no-coinbase por bloque (default: 3)",
    )
    sub.add_argument(
        "--block-interval-seconds",
        type=float,
        default=10.0,
        help="intervalo máximo entre intentos de minado (default: 10)",
    )
    sub.add_argument(
        "--mining-reward",
        type=int,
        default=50,
        help="recompensa por bloque minado (default: 50)",
    )
    sub.add_argument(
        "--genesis-seed",
        type=str,
        default=None,
        help="semilla del génesis (o env HASHCOIN_GENESIS_SEED)",
    )
    sub.add_argument(
        "--shared-key",
        type=str,
        default=None,
        help="clave simétrica base64 (o env HASHCOIN_SHARED_KEY)",
    )
    sub.add_argument(
        "--genesis-prefund-accounts",
        type=int,
        default=5,
        help="cuentas pre-fondeadas en el génesis (default: 5)",
    )
    sub.add_argument(
        "--genesis-prefund-amount",
        type=int,
        default=1000,
        help="saldo inicial por cuenta pre-fondeada (default: 1000)",
    )
    sub.add_argument(
        "--reconnect-delay-seconds",
        type=float,
        default=3.0,
        help="delay entre reintentos de conexión a peers (default: 3)",
    )
    sub.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="nivel de log del nodo (DEBUG/INFO/WARNING)",
    )
    sub.add_argument(
        "--verbose",
        action="store_true",
        help="logs en nivel DEBUG",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hashcoin",
        description="HashCoin — CLI local para nodos y billetera",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python hashcoin.py node start\n"
            "  python hashcoin.py wallet --generator --generator-users 5\n"
            "  python hashcoin.py network\n\n"
            "Variables de entorno: HASHCOIN_GENESIS_SEED, HASHCOIN_SHARED_KEY"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    node_parser = subparsers.add_parser(
        "node",
        help="operaciones sobre un nodo",
        description="Gestión de nodos HashCoin",
    )
    node_sub = node_parser.add_subparsers(dest="node_command", required=True)

    start_parser = node_sub.add_parser(
        "start",
        help="levantar un nodo con defaults de desarrollo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Inicia un nodo; genera claves y BD bajo ./data/<node-id>/ si hace falta.",
    )
    _add_node_start_parser(start_parser)

    node_sub.add_parser(
        "help",
        help="ayuda detallada del subcomando node",
        description=NODE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    wallet_parser = subparsers.add_parser(
        "wallet",
        help="consola de billetera",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=WALLET_HELP.strip(),
    )
    wallet_parser.add_argument(
        "--node-url",
        type=str,
        default="http://127.0.0.1:9081",
        help="URL HTTP del nodo (default: http://127.0.0.1:9081)",
    )
    wallet_parser.add_argument(
        "--fallback-node-url",
        type=str,
        default="",
        help="URL alternativa del nodo",
    )
    wallet_parser.add_argument(
        "--keys-dir",
        type=str,
        default="./wallet-keys",
        help="directorio de claves de usuario (default: ./wallet-keys)",
    )
    wallet_parser.add_argument(
        "--genesis-seed",
        type=str,
        default=None,
        help="semilla del génesis (o env HASHCOIN_GENESIS_SEED)",
    )
    wallet_parser.add_argument(
        "--generator",
        action="store_true",
        help="modo generador de transacciones de prueba",
    )
    wallet_parser.add_argument(
        "--generator-users",
        type=int,
        default=5,
        help="cuentas del generador (default: 5)",
    )
    wallet_parser.add_argument(
        "--generator-interval-seconds",
        type=float,
        default=2.0,
        help="intervalo del generador en segundos (default: 2.0)",
    )

    subparsers.add_parser(
        "network",
        help="muestra comandos para levantar una red de ejemplo",
        description=NETWORK_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "node" and args.node_command == "help":
        print(NODE_HELP)
        return 0

    if args.command == "network":
        print(NETWORK_HELP)
        return 0

    if args.command == "node" and args.node_command == "start":
        run_argv = _node_start_argv(args)
    elif args.command == "wallet":
        run_argv = _wallet_argv(args)
    else:
        parser.print_help()
        return 1

    from run import main as run_main

    return run_main(run_argv[1:])


if __name__ == "__main__":
    sys.exit(main())
