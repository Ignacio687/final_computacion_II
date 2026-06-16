"""DTO serializable de Block para JSON sobre TCP y persistencia SQLite.

Convenciones (ver doc/protocolo.md §5):
    - id: altura del bloque (entero secuencial; génesis = 0).
    - timestamp: epoch en segundos (float, UTC).
    - target: cantidad de ceros hexadecimales requeridos al inicio del hash.
    - transactions: lista completa de TransactionDTO (no solo ids), en orden.
"""

from dataclasses import dataclass
from typing import List

from main.repository.dto.transaction_dto import TransactionDTO


@dataclass(frozen=True)
class BlockDTO:
    """Representación serializable de un bloque."""

    id: int
    last_hash: str
    hash: str
    timestamp: float
    target: int
    nonce: int
    transactions: List[TransactionDTO]
