"""Consola interactiva de la billetera (modo no-generador).

Permite por línea de comandos consultar y operar contra un nodo vía WalletClient:
- ver balance de una dirección,
- listar transacciones,
- ver estado del nodo,
- crear/seleccionar una cuenta y enviar una transacción manual.
"""

from main.wallet.wallet_client import WalletClient
from main.wallet.key_store import KeyStore


class WalletConsole:
    """Bucle de consola que traduce comandos del usuario a llamadas de WalletClient."""

    def __init__(self, client: WalletClient, key_store: KeyStore) -> None:
        self._client = client
        self._key_store = key_store

    def run(self) -> int:
        """Ejecuta el bucle interactivo hasta que el usuario sale. Devuelve el código de salida."""
        raise NotImplementedError
