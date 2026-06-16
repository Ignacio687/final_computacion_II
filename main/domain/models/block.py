"""Entidad bloque de la blockchain. Solo declaración de atributos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from main.domain.models.transaction import Transaction


@dataclass(frozen=False)
class Block:
    """Bloque de la cadena. Ver contrato canónico en doc/protocolo.md §5.

    - id: ALTURA del bloque (entero secuencial; génesis = 0). Es la clave de orden y
      persistencia, NO es el hash.
    - hash: hash PoW del bloque (sha256 de los bytes hasheables, §5.1). Debe empezar con
      `target` ceros hex.
    - last_hash: hash del bloque previo ("0"*64 en el génesis).
    - timestamp: instante de creación (en memoria es datetime; en DTO/red/persistencia
      viaja como epoch float UTC).
    - target: dificultad PoW (cantidad de ceros hex iniciales requeridos).
    """

    id: int
    last_hash: str
    hash: str
    timestamp: datetime
    target: int  # dificultad PoW
    nonce: int
    transactions: List["Transaction"]
