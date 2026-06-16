"""Configuración y utilidades de logging por nodo (sin secretos en consola)."""

from __future__ import annotations

import contextvars
import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main.domain.models.message import Message

_node_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "hashcoin_node_id", default="?"
)
_logging_configured = False


class _NodeFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.node_id = _node_id.get()
        return True


def set_node_log_context(node_id: str) -> contextvars.Token[str]:
    """Fija el node_id del hilo/tarea actual para el prefijo de logs."""
    return _node_id.set(node_id)


def reset_node_log_context(token: contextvars.Token[str]) -> None:
    _node_id.reset(token)


def trunc(value: str | bytes | None, n: int = 12) -> str:
    """Trunca ids/hashes para no volcar payloads completos en consola."""
    if value is None:
        return "?"
    text = (
        value.decode("utf-8", errors="replace")
        if isinstance(value, bytes)
        else str(value)
    )
    if len(text) <= n:
        return text
    return f"{text[:n]}..."


def configure_logging(
    node_id: str,
    *,
    verbose: bool = False,
    log_level: str = "INFO",
) -> None:
    """Configura logging global con prefijo [node_id] en stderr."""
    global _logging_configured
    set_node_log_context(node_id)

    if _logging_configured:
        return

    level_name = "DEBUG" if verbose else log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("[%(node_id)s] %(levelname)s %(message)s")
    )
    handler.addFilter(_NodeFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def message_detail(message: Message) -> str:
    """Resumen legible del mensaje sin firmas, claves ni payloads completos."""
    from main.domain.models.message import MessageType
    from main.domain.models.payloads import (
        ChainResponsePayload,
        GetChainPayload,
        HelloPayload,
        MempoolResponsePayload,
        NewBlockPayload,
        NewTxPayload,
    )

    msg_type = message.type.value
    payload = message.payload

    if message.type == MessageType.HELLO and isinstance(payload, HelloPayload):
        return f"{msg_type} node_id={payload.node_id} listen_port={payload.listen_port}"
    if message.type == MessageType.NEW_TX and isinstance(payload, NewTxPayload):
        tx = payload.transaction
        return f"{msg_type} tx_id={trunc(tx.id)}"
    if message.type == MessageType.NEW_BLOCK and isinstance(payload, NewBlockPayload):
        block = payload.block
        return (
            f"{msg_type} block_id={block.id} hash={trunc(block.hash)} "
            f"txs={len(block.transactions)}"
        )
    if message.type == MessageType.GET_CHAIN and isinstance(payload, GetChainPayload):
        return f"{msg_type} since_height={payload.since_height}"
    if message.type == MessageType.CHAIN_RESPONSE and isinstance(
        payload, ChainResponsePayload
    ):
        if not payload.blocks:
            return f"{msg_type} blocks=0"
        first = payload.blocks[0].id
        last = payload.blocks[-1].id
        return f"{msg_type} blocks={len(payload.blocks)} range={first}-{last}"
    if message.type == MessageType.GET_MEMPOOL:
        return f"{msg_type}"
    if message.type == MessageType.MEMPOOL_RESPONSE and isinstance(
        payload, MempoolResponsePayload
    ):
        return f"{msg_type} txs={len(payload.transactions)}"
    return msg_type
