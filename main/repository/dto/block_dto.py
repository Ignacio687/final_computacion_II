"""DTO serializable de Block para JSON sobre TCP y persistencia SQLite.

Convenciones:
    - timestamp: epoch en segundos (float).
    - target: cantidad de ceros hexadecimales requeridos al inicio del hash.
    - transactions: lista completa de TransactionDTO (no solo ids).
"""

from dataclasses import dataclass
from typing import List

from main.repository.dto.transaction_dto import TransactionDTO


@dataclass(frozen=True)
class BlockDTO:
    """Representación serializable de un bloque."""

    id: str
    last_hash: str
    hash: str
    timestamp: float
    target: int
    nonce: int
    transactions: List[TransactionDTO]
