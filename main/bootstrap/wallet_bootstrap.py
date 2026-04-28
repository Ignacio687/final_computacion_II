"""Composición de la billetera: instanciación e inyección de dependencias."""

from main.config.wallet_config import WalletConfig


def run_wallet(config: WalletConfig) -> int:
    """Crea WalletClient(config.node_url) y, según `generator_mode`:
        - False: lanza la consola interactiva (consultas y envío manual de tx).
        - True : lanza el generador que crea `generator_users` usuarios aleatorios
                 y envía transacciones cada `generator_interval_seconds`.

    Devuelve el código de salida (0 si terminó correctamente).
    """
    raise NotImplementedError
