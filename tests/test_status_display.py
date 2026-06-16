from types import SimpleNamespace

from main.wallet.status_display import (
    collect_status_accounts,
    format_status_output,
    parse_status_args,
    truncate_address,
)


def _account(address: str):
    return SimpleNamespace(id=address)


def test_truncate_address_short_unchanged():
    addr = "abcd1234"
    assert truncate_address(addr) == addr


def test_truncate_address_long():
    addr = "a" * 20 + "b" * 20
    assert truncate_address(addr) == f"{'a' * 8}...{'b' * 8}"


def test_collect_status_accounts_genesis_and_local():
    genesis = [_account("genesis-address-1"), _account("genesis-address-2")]
    local = [_account("local-address-1")]

    rows = collect_status_accounts(
        local,
        genesis,
        balance_lookup=lambda address: {"genesis-address-1": 100, "local-address-1": 5}.get(
            address, 0
        ),
    )

    assert [row.alias for row in rows] == ["genesis-0", "genesis-1", "local-ad"]
    assert rows[0].balance == 100
    assert rows[2].balance == 5


def test_collect_status_accounts_deduplicates_genesis_in_keys_dir():
    shared = _account("shared-address")
    rows = collect_status_accounts(
        [shared],
        [shared],
        balance_lookup=lambda _: 42,
    )
    assert len(rows) == 1
    assert rows[0].alias == "genesis-0"


def test_collect_status_accounts_hides_zero_local_by_default():
    rows = collect_status_accounts(
        [_account("empty-local"), _account("funded-local")],
        balance_lookup=lambda address: 99 if address == "funded-local" else 0,
    )
    assert len(rows) == 1
    assert rows[0].address == "funded-local"


def test_format_status_output_includes_node_and_accounts():
    status = {
        "node_id": "node-a",
        "height": 3,
        "difficulty": 2,
        "mempool_size": 1,
        "peers_connected": 2,
        "total_supply": 5000,
    }
    accounts = collect_status_accounts(
        [_account("abcd1234efgh5678ijkl9012mnop3456")],
        balance_lookup=lambda _: 50,
    )
    output = format_status_output(status, accounts, live=True, interval_seconds=5)

    assert "node_id=node-a height=3" in output
    assert "mempool_size=1 peers_connected=2" in output
    assert "abcd1234...mnop3456" in output
    assert "balance=50" in output
    assert "total_supply (red)=5000" in output
    assert "Actualizando cada 5s" in output


def test_format_status_output_empty_accounts():
    output = format_status_output({"total_supply": 5000}, [], live=False)
    assert "sin cuentas con saldo" in output


def test_parse_status_args_defaults_to_live():
    mode, interval = parse_status_args(["status"], default_interval=5.0)
    assert mode == "live"
    assert interval == 5.0


def test_parse_status_args_once_and_custom_interval():
    mode, interval = parse_status_args(
        ["status", "once", "--interval", "2.5"], default_interval=5.0
    )
    assert mode == "once"
    assert interval == 2.5


def test_parse_status_args_live_explicit():
    mode, interval = parse_status_args(
        ["status", "live", "--interval", "10"], default_interval=5.0
    )
    assert mode == "live"
    assert interval == 10.0


def test_parse_status_args_rejects_invalid_interval():
    try:
        parse_status_args(["status", "--interval", "0"], default_interval=5.0)
    except ValueError as exc:
        assert "mayor que cero" in str(exc)
    else:
        raise AssertionError("expected ValueError")
