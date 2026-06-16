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
from main.wallet.console import WalletConsole
from main.wallet.key_store import KeyStore
from main.wallet.tx_generator import TransactionGenerator
from main.wallet.wallet_client import WalletClient


def run_wallet(config: WalletConfig) -> int:
    """Crea WalletClient + KeyStore y, según `generator_mode`:
        - False: lanza la consola interactiva (consultas y envío manual de tx).
        - True : lanza el generador que deriva cuentas pre-fondeadas del génesis y envía
                 transacciones cada `generator_interval_seconds`.

    Devuelve el código de salida (0 si terminó correctamente).
    """
    client = WalletClient(config.node_url, config.fallback_node_urls)
    key_store = KeyStore(config.keys_dir)

    if config.generator_mode:
        generator = TransactionGenerator(
            client,
            key_store,
            config.genesis_seed,
            config.generator_users,
            config.generator_interval_seconds,
        )
        return generator.run()

    console = WalletConsole(
        client,
        key_store,
        genesis_seed=config.genesis_seed,
        genesis_prefund_accounts=config.genesis_prefund_accounts,
        status_interval_seconds=config.status_interval_seconds,
    )
    return console.run()
