"""Adaptador: verificación de cadena completa (para workers con queue.Queue)."""

from typing import List

from main.application.interfaces.chain_verifier import IChainVerifier
from main.application.interfaces.block_validator import IBlockValidator
from main.domain.models.block import Block


class DefaultChainVerifier(IChainVerifier):
    """Implementación de IChainVerifier; usa IBlockValidator por bloque."""

    def __init__(self, block_validator: IBlockValidator) -> None:
        self._block_validator = block_validator

    def verify_chain(self, blocks: List[Block]) -> bool:
        raise NotImplementedError
