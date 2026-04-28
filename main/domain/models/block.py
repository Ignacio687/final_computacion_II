"""Entidad bloque de la blockchain. Solo declaración de atributos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from main.domain.models.transaction import Transaction


@dataclass(frozen=False)
class Block:
    """Bloque de la cadena. id, last_hash, hash, timestamp, target, nonce, lista de transacciones."""

    id: str
    last_hash: str
    hash: str
    timestamp: datetime
    target: int  # dificultad PoW
    nonce: int
    transactions: List["Transaction"]
