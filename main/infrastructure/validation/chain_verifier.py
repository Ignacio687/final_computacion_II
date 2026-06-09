"""Adaptador: verificación de cadena completa (para workers con queue.Queue)."""

from typing import Dict, List

from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.chain_verifier import IChainVerifier
from main.application.interfaces.genesis_provider import IGenesisProvider
from main.domain.models.block import Block
from main.infrastructure.validation.block_validator import DefaultBlockValidator


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
        if not blocks:
            return False

        expected_genesis = self._genesis_provider.get_genesis_block()
        if blocks[0].id != expected_genesis.id or blocks[0].hash != expected_genesis.hash:
            return False

        seen_tx_ids: set[str] = set()
        for tx in blocks[0].transactions:
            if tx.id in seen_tx_ids:
                return False
            seen_tx_ids.add(tx.id)

        balances: Dict[str, int] = {}
        for tx in blocks[0].transactions:
            balances[tx.receiver_id] = balances.get(tx.receiver_id, 0) + tx.amount

        for index in range(1, len(blocks)):
            previous = blocks[index - 1]
            current = blocks[index]

            if current.last_hash != previous.hash:
                return False
            if current.timestamp <= previous.timestamp:
                return False

            if isinstance(self._block_validator, DefaultBlockValidator):
                if not self._block_validator.validate_with_balances(
                    current, previous.hash, balances
                ):
                    return False
            elif not self._block_validator.validate(current, previous.hash):
                return False

            for tx in current.transactions:
                if tx.id in seen_tx_ids:
                    return False
                seen_tx_ids.add(tx.id)

        return True
