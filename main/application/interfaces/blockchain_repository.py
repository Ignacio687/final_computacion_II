"""Interfaz: persistencia y lectura de la blockchain."""

from abc import ABC, abstractmethod
from typing import List

from main.domain.models.block import Block


class IBlockchainRepository(ABC):
    """Contrato para persistir y recuperar la cadena de bloques."""

    @abstractmethod
    def get_chain(self) -> List[Block]:
        """Devuelve la cadena completa, en orden ascendente de altura (génesis primero)."""
        ...

    @abstractmethod
    def get_chain_since(self, height: int) -> List[Block]:
        """Devuelve los bloques desde la altura indicada (inclusive). 0 = cadena completa.
        Si height >= get_height(), devuelve lista vacía."""
        ...

    @abstractmethod
    def append_block(self, block: Block) -> None:
        """Persiste el bloque al final de la cadena. No valida; la validación es responsabilidad
        de IBlockValidator antes de llamar a este método."""
        ...

    @abstractmethod
    def replace_chain(self, blocks: List[Block]) -> None:
        """Reemplaza la cadena entera por la lista dada (sincronización con peer cuando llega
        una cadena más larga y válida). No valida la cadena: la validación es responsabilidad
        de IChainVerifier antes de llamar."""
        ...

    @abstractmethod
    def get_last_block(self) -> Block | None:
        """Último bloque de la cadena, o None si la cadena está vacía."""
        ...

    @abstractmethod
    def get_height(self) -> int:
        """Cantidad de bloques en la cadena (0 si está vacía; 1 cuando solo está el génesis)."""
        ...
