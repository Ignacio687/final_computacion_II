from main.wallet.status_display import (
    STATUS_ACCOUNTS_LIMIT,
    build_status_account_rows,
    format_status_output,
    parse_status_args,
    truncate_address,
)


def test_truncate_address_short_unchanged():
    addr = "abcd1234"
    assert truncate_address(addr) == addr


def test_truncate_address_long():
    addr = "a" * 20 + "b" * 20
    assert truncate_address(addr) == f"{'a' * 8}...{'b' * 8}"


def test_build_status_account_rows_uses_aliases():
    active = [
        {"address": "genesis-address-1", "balance": 100, "last_block_id": 5},
        {"address": "other-address-2", "balance": 50, "last_block_id": 10},
    ]
    rows = build_status_account_rows(
        active,
        alias_for_address={"genesis-address-1": "genesis-0"},
    )
    assert rows[0].alias == "genesis-0"
    assert rows[0].balance == 100
    assert rows[0].last_block_id == 5
    assert rows[1].alias == "other-ad"


def test_format_status_output_includes_node_and_accounts():
    status = {
        "node_id": "node-a",
        "height": 3,
        "difficulty": 2,
        "mempool_size": 1,
        "peers_connected": 2,
        "total_supply": 5000,
    }
    accounts = build_status_account_rows(
        [
            {
                "address": "abcd1234efgh5678ijkl9012mnop3456",
                "balance": 50,
                "last_block_id": 3,
            }
        ]
    )
    output = format_status_output(status, accounts, live=True, interval_seconds=5)

    assert "node_id=node-a height=3" in output
    assert "top 1 por última actividad" in output
    assert "abcd1234...mnop3456" in output
    assert "balance=50" in output
    assert "blk=3" in output
    assert "total_supply (red)=5000" in output
    assert "Actualizando cada 5s" in output


def test_format_status_output_empty_accounts():
    output = format_status_output({"total_supply": 5000}, [], live=False)
    assert "sin cuentas confirmadas" in output


def test_status_accounts_limit_default():
    assert STATUS_ACCOUNTS_LIMIT == 20


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
