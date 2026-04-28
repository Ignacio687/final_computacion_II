"""Interfaz: cálculo y verificación de PoW (minado)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from main.domain.models.block import Block


@dataclass(frozen=True)
class MiningResult:
    """Resultado del minado: nonce encontrado y hash final del bloque."""

    nonce: int
    block_hash: str


class IProofOfWork(ABC):
    """Contrato para resolver y verificar el PoW de un bloque.
    `mine` es CPU-bound y bloqueante; se ejecuta en ProcessPoolExecutor."""

    @abstractmethod
    def mine(self, block_candidate: Block) -> MiningResult:
        """Itera nonce desde 0 hasta encontrar un hash que cumpla la dificultad
        `block_candidate.target` (cantidad de ceros hex iniciales). Devuelve nonce y hash."""
        ...

    @abstractmethod
    def verify(self, block: Block) -> bool:
        """Devuelve True si `block.hash` es el hash correcto del bloque (re-calculado con
        sus campos y `block.nonce`) y cumple la dificultad `block.target`."""
        ...
