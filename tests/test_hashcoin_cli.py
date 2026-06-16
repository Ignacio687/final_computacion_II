"""Tests del CLI hashcoin (argparse y delegación a run.py)."""

import subprocess
import sys
from pathlib import Path

import pytest

from hashcoin import (
    DEFAULT_GENESIS_SEED,
    DEFAULT_SHARED_KEY,
    _ensure_node_keys,
    _node_start_argv,
    _wallet_argv,
    main,
)


def test_hashcoin_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "hashcoin.py", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0
    assert "node" in result.stdout
    assert "wallet" in result.stdout


def test_hashcoin_node_help():
    result = subprocess.run(
        [sys.executable, "hashcoin.py", "node", "help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0
    assert "pow-workers" in result.stdout.lower() or "ProcessPool" in result.stdout


def test_hashcoin_network_prints_examples():
    result = subprocess.run(
        [sys.executable, "hashcoin.py", "network"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0
    assert "node1" in result.stdout
    assert "9081" in result.stdout


def test_node_start_argv_defaults():
    import argparse

    from hashcoin import _add_node_start_parser

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="node_command")
    start = sub.add_parser("start")
    _add_node_start_parser(start)
    args = parser.parse_args(["start"])
    argv = _node_start_argv(args)

    assert argv[0:2] == ["run.py", "node"]
    assert "--node-id" in argv and "node1" in argv
    assert "--difficulty" in argv and "2" in argv
    assert "--pow-workers" in argv
    assert "--min-tx-per-block" in argv and "3" in argv
    assert "--block-interval-seconds" in argv and "10.0" in argv
    assert "--mining-reward" in argv and "50" in argv
    assert "--genesis-seed" in argv and DEFAULT_GENESIS_SEED in argv
    assert "--shared-key" in argv and DEFAULT_SHARED_KEY in argv
    db_index = argv.index("--db-path")
    assert argv[db_index + 1].endswith("data/node1/node.db")


def test_ensure_node_keys_idempotent(tmp_path: Path):
    keys_dir = tmp_path / "keys"
    priv1, pub1, addr1 = _ensure_node_keys(keys_dir)
    priv2, pub2, addr2 = _ensure_node_keys(keys_dir)
    assert priv1 == priv2
    assert pub1 == pub2
    assert addr1 == addr2
    assert len(addr1) == 64


def test_wallet_argv_generator():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--node-url", default="http://127.0.0.1:9081")
    parser.add_argument("--fallback-node-url", default="")
    parser.add_argument("--keys-dir", default="./wallet-keys")
    parser.add_argument("--genesis-seed", default=None)
    parser.add_argument("--generator", action="store_true")
    parser.add_argument("--generator-users", type=int, default=5)
    parser.add_argument("--generator-interval-seconds", type=float, default=2.0)
    args = parser.parse_args(["--generator", "--generator-users", "3"])
    argv = _wallet_argv(args)
    assert "--generator" in argv
    assert "--generator-users" in argv and "3" in argv


def test_main_network_command(capsys):
    assert main(["network"]) == 0
    captured = capsys.readouterr()
    assert "node2" in captured.out
