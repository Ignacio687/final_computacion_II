"""Adaptador: bloque génesis derivado de una semilla string."""

from main.application.interfaces.genesis_provider import IGenesisProvider
from main.domain.models.block import Block


class SeedGenesisProvider(IGenesisProvider):
    """Implementación de IGenesisProvider. Construye el bloque génesis a partir de una
    semilla compartida por toda la red:
        - id: SHA-256(seed) en hex (primeros 32 chars).
        - last_hash: '0' * 64.
        - hash: SHA-256 del bloque (con nonce=0, target=0, transactions=[]).
        - timestamp: epoch fijo derivado de la semilla.
        - target: 0 (no requiere PoW).
        - nonce: 0.
        - transactions: lista vacía."""

    def __init__(self, seed: str) -> None:
        self._seed = seed

    def get_genesis_block(self) -> Block:
        raise NotImplementedError
