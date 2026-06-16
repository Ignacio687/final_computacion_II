"""Formateo del comando `status` de la billetera (nodo + cuentas locales)."""

from dataclasses import dataclass
from typing import Callable, Iterable, Protocol


class BalanceLookup(Protocol):
    def __call__(self, address: str) -> int: ...


@dataclass(frozen=True)
class StatusAccountRow:
    alias: str
    address: str
    balance: int


def truncate_address(address: str, head: int = 8, tail: int = 8) -> str:
    if len(address) <= head + tail + 3:
        return address
    return f"{address[:head]}...{address[-tail:]}"


def collect_status_accounts(
    local_accounts: Iterable[object],
    genesis_accounts: Iterable[object] | None = None,
    balance_lookup: BalanceLookup | None = None,
) -> list[StatusAccountRow]:
    """Combina cuentas de keys_dir y génesis (sin duplicar por dirección)."""
    rows: list[StatusAccountRow] = []
    seen: set[str] = set()

    if genesis_accounts:
        for index, account in enumerate(genesis_accounts):
            address = account.id
            if address in seen:
                continue
            seen.add(address)
            balance = balance_lookup(address) if balance_lookup else 0
            rows.append(
                StatusAccountRow(
                    alias=f"genesis-{index}",
                    address=address,
                    balance=balance,
                )
            )

    for account in local_accounts:
        address = account.id
        if address in seen:
            continue
        seen.add(address)
        balance = balance_lookup(address) if balance_lookup else 0
        rows.append(
            StatusAccountRow(
                alias=address[:8],
                address=address,
                balance=balance,
            )
        )

    return rows


def format_status_output(
    status: dict,
    accounts: list[StatusAccountRow],
    *,
    live: bool = False,
    interval_seconds: float | None = None,
) -> str:
    lines = [
        "=== HashCoin wallet status ===",
        (
            f"node_id={status.get('node_id')} "
            f"height={status.get('height')} "
            f"difficulty={status.get('difficulty')} "
            f"mempool_size={status.get('mempool_size')} "
            f"peers_connected={status.get('peers_connected')}"
        ),
        "",
        "Cuentas:",
    ]
    if not accounts:
        lines.append("  (sin cuentas)")
    else:
        alias_width = max(len(row.alias) for row in accounts)
        for row in accounts:
            lines.append(
                f"  {row.alias:<{alias_width}}  "
                f"{truncate_address(row.address):<22}  "
                f"balance={row.balance}"
            )
    if live and interval_seconds is not None:
        lines.append("")
        lines.append(
            f"Actualizando cada {interval_seconds:g}s (Ctrl+C para volver al prompt)"
        )
    return "\n".join(lines)


def parse_status_args(parts: list[str], default_interval: float) -> tuple[str, float]:
    """Devuelve (modo, intervalo) con modo en {'live', 'once'}."""
    mode = "live"
    interval = default_interval
    index = 1
    while index < len(parts):
        token = parts[index]
        if token == "live":
            mode = "live"
            index += 1
            continue
        if token == "once":
            mode = "once"
            index += 1
            continue
        if token == "--interval" and index + 1 < len(parts):
            interval = float(parts[index + 1])
            if interval <= 0:
                raise ValueError("El intervalo debe ser mayor que cero")
            index += 2
            continue
        raise ValueError(
            "Uso: status [live|once] [--interval <segundos>]"
        )
    return mode, interval


ANSI_CLEAR_SCREEN = "\033[2J\033[H"
