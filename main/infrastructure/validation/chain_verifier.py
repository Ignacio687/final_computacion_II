"""Adaptador: verificación de cadena completa (para workers con queue.Queue)."""

from typing import List

from main.application.interfaces.chain_verifier import IChainVerifier
from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.genesis_provider import IGenesisProvider
from main.domain.models.block import Block


class DefaultChainVerifier(IChainVerifier):
    """Implementación de IChainVerifier (ver doc/protocolo.md §5.4).

    - block_validator: valida cada bloque y su encadenamiento.
    - genesis_provider: provee el génesis esperado para exigir que `blocks[0]` sea
      idéntico (mismo id y hash).
    """

    def __init__(
        self,
        block_validator: IBlockValidator,
        genesis_provider: IGenesisProvider,
    ) -> None:
        self._block_validator = block_validator
        self._genesis_provider = genesis_provider

    def verify_chain(self, blocks: List[Block]) -> bool:
        raise NotImplementedError
