"""Composición de la billetera: instanciación e inyección de dependencias.

Orden de construcción:

    client = WalletClient(config.node_url)
    key_store = KeyStore(config.keys_dir)

    if config.generator_mode:
        generator = TransactionGenerator(
            client, key_store, config.genesis_seed,
            config.generator_users, config.generator_interval_seconds,
        )
        return generator.run()
    else:
        console = WalletConsole(client, key_store)
        return console.run()
"""

from main.config.wallet_config import WalletConfig


def run_wallet(config: WalletConfig) -> int:
    """Crea WalletClient + KeyStore y, según `generator_mode`:
        - False: lanza la consola interactiva (consultas y envío manual de tx).
        - True : lanza el generador que deriva cuentas pre-fondeadas del génesis y envía
                 transacciones cada `generator_interval_seconds`.

    Devuelve el código de salida (0 si terminó correctamente).
    """
    raise NotImplementedError
