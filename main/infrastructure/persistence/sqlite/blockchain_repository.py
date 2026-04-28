"""Adaptador: persistencia de la blockchain en SQLite."""

from typing import List

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.domain.models.block import Block


class SQLiteBlockchainRepository(IBlockchainRepository):
    """Implementación de IBlockchainRepository usando SQLite. Crea las tablas si no existen
    al instanciarse. db_path es la ruta del archivo SQLite (un archivo por nodo)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_chain(self) -> List[Block]:
        raise NotImplementedError

    def get_chain_since(self, height: int) -> List[Block]:
        raise NotImplementedError

    def append_block(self, block: Block) -> None:
        raise NotImplementedError

    def replace_chain(self, blocks: List[Block]) -> None:
        raise NotImplementedError

    def get_last_block(self) -> Block | None:
        raise NotImplementedError

    def get_height(self) -> int:
        raise NotImplementedError
