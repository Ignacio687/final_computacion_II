"""Adaptador: bloque génesis derivado de una semilla string."""

from main.application.interfaces.genesis_provider import IGenesisProvider
from main.domain.models.block import Block


class SeedGenesisProvider(IGenesisProvider):
    """Implementación de IGenesisProvider (ver doc/protocolo.md §8). Construye el bloque
    génesis de forma determinista a partir de una semilla compartida por toda la red:
        - id: 0 (altura del génesis).
        - last_hash: '0' * 64.
        - timestamp: 0.0 (constante fija).
        - target: 0 (no requiere PoW).
        - nonce: 0.
        - transactions: una tx de fondeo 'GENESIS' por cada cuenta pre-fondeada, en orden
          i ascendente. Las claves se derivan de la semilla con
          `sha256(f"{seed}|prefund|{i}")` -> Ed25519 (las mismas que deriva la billetera
          generadora). Cada tx fondea `prefund_amount`. Detalle exacto en §8.
        - hash: SHA-256 del bloque sobre esas transacciones (§5.1).
    """

    def __init__(self, seed: str, prefund_accounts: int, prefund_amount: int) -> None:
        self._seed = seed
        self._prefund_accounts = prefund_accounts
        self._prefund_amount = prefund_amount

    def get_genesis_block(self) -> Block:
        raise NotImplementedError
