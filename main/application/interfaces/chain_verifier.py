"""Interfaz: verificación pesada de una cadena entera."""

from abc import ABC, abstractmethod
from typing import List

from main.domain.models.block import Block


class IChainVerifier(ABC):
    """Contrato para verificar una cadena completa.
    Llamado desde un worker thread (queue.Queue + threading)."""

    @abstractmethod
    def verify_chain(self, blocks: List[Block]) -> bool:
        """Devuelve True si y solo si:

        1. `blocks[0]` es exactamente el bloque génesis conocido (mismo id, mismo hash).
        2. Para cada i > 0: `blocks[i].last_hash == blocks[i-1].hash`.
        3. Cada bloque pasa IBlockValidator.validate(block, previous_hash).
        4. Las transacciones no se repiten dentro de la cadena.
        """
        ...
