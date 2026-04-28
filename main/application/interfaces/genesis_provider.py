"""Interfaz: proveedor del bloque génesis."""

from abc import ABC, abstractmethod

from main.domain.models.block import Block


class IGenesisProvider(ABC):
    """Contrato para producir el bloque génesis. Debe ser determinista para una semilla dada,
    de modo que todos los nodos arranquen con el mismo bloque génesis."""

    @abstractmethod
    def get_genesis_block(self) -> Block:
        """Devuelve el bloque génesis. Mismas entradas (semilla) producen siempre el mismo bloque."""
        ...
