"""Formateo del comando `status` de la billetera (nodo + cuentas activas)."""

from dataclasses import dataclass
from typing import Mapping, Protocol

STATUS_ACCOUNTS_LIMIT = 20


class BalanceLookup(Protocol):
    def __call__(self, address: str) -> int: ...


@dataclass(frozen=True)
class StatusAccountRow:
    alias: str
    address: str
    balance: int
    last_block_id: int | None = None


def truncate_address(address: str, head: int = 8, tail: int = 8) -> str:
    if len(address) <= head + tail + 3:
        return address
    return f"{address[:head]}...{address[-tail:]}"


def build_status_account_rows(
    active_accounts: list[dict],
    *,
    alias_for_address: Mapping[str, str] | None = None,
) -> list[StatusAccountRow]:
    """Convierte respuesta GET /accounts en filas para mostrar."""
    aliases = alias_for_address or {}
    rows: list[StatusAccountRow] = []
    for item in active_accounts:
        address = item["address"]
        rows.append(
            StatusAccountRow(
                alias=aliases.get(address, address[:8]),
                address=address,
                balance=int(item["balance"]),
                last_block_id=int(item["last_block_id"]),
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
    shown_total = sum(row.balance for row in accounts)
    network_total = status.get("total_supply")
    lines = [
        "=== HashCoin wallet status ===",
        (
            f"node_id={status.get('node_id')} "
            f"height={status.get('height')} "
            f"difficulty={status.get('difficulty')} "
            f"mempool_size={status.get('mempool_size')} "
            f"peers_connected={status.get('peers_connected')}"
        ),
    ]
    if network_total is not None:
        lines.append(f"total_supply (red)={network_total}")
    lines.extend(
        [
            "",
            f"Cuentas (top {len(accounts)} por última actividad en cadena):",
        ]
    )
    if not accounts:
        lines.append("  (sin cuentas confirmadas)")
    else:
        alias_width = max(len(row.alias) for row in accounts)
        for row in accounts:
            block_hint = (
                f"  blk={row.last_block_id}" if row.last_block_id is not None else ""
            )
            lines.append(
                f"  {row.alias:<{alias_width}}  "
                f"{truncate_address(row.address):<22}  "
                f"balance={row.balance}{block_hint}"
            )
    lines.append("")
    lines.append(f"Suma mostrada: {shown_total}")
    if network_total is not None and shown_total < network_total:
        lines.append(
            f"El resto ({network_total - shown_total}) está en otras direcciones "
            f"no listadas aquí."
        )
    lines.append(
        "Nota: cada bloque minado emite recompensa; el total de la red crece con el tiempo."
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
