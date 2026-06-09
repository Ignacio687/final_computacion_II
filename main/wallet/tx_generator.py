"""Generador de transacciones de prueba (modo --generator).

Alimenta la red con tráfico sin usuarios reales. Para que las transacciones sean válidas,
parte de las cuentas pre-fondeadas del génesis (derivadas de la semilla compartida, ver
doc/protocolo.md §8) y va moviendo fondos entre ellas y nuevas cuentas.

Flujo:
1. Derivar las cuentas pre-fondeadas con KeyStore.derive_genesis_accounts(genesis_seed, N).
2. Periódicamente (cada `interval_seconds`): elegir un emisor con saldo, un receptor y un
   monto válido (<= balance consultado al nodo), construir la tx firmada (tx_builder) y
   enviarla por POST /tx.
"""

from main.wallet.wallet_client import WalletClient
from main.wallet.key_store import KeyStore


class TransactionGenerator:
    """Genera y envía transacciones de prueba a un nodo a intervalos regulares."""

    def __init__(
        self,
        client: WalletClient,
        key_store: KeyStore,
        genesis_seed: str,
        users: int,
        interval_seconds: float,
    ) -> None:
        self._client = client
        self._key_store = key_store
        self._genesis_seed = genesis_seed
        self._users = users
        self._interval_seconds = interval_seconds

    def run(self) -> int:
        """Bucle de generación hasta interrupción. Devuelve el código de salida."""
        raise NotImplementedError
