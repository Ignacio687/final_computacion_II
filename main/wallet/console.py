"""Consola interactiva de la billetera (modo no-generador).

Permite por línea de comandos consultar y operar contra un nodo vía WalletClient:
- ver balance de una dirección,
- listar transacciones,
- ver estado del nodo,
- crear/seleccionar una cuenta y enviar una transacción manual.
"""

from main.wallet.wallet_client import WalletClient
from main.wallet.key_store import KeyStore
from main.wallet.tx_builder import build_signed_transaction


class WalletConsole:
    """Bucle de consola que traduce comandos del usuario a llamadas de WalletClient."""

    _HELP = (
        "Comandos:\n"
        "  help                              muestra esta ayuda\n"
        "  balance <address>                 consulta el saldo de una dirección\n"
        "  transactions [address] [limit]    lista transacciones confirmadas\n"
        "  status                            estado del nodo\n"
        "  accounts                          lista cuentas locales\n"
        "  create                            crea una cuenta nueva\n"
        "  send <from> <to> <amount>         envía una transacción firmada\n"
        "  quit | exit                       sale de la consola"
    )

    def __init__(self, client: WalletClient, key_store: KeyStore) -> None:
        self._client = client
        self._key_store = key_store

    def run(self) -> int:
        """Ejecuta el bucle interactivo hasta que el usuario sale. Devuelve el código de salida."""
        print("HashCoin billetera. Escriba 'help' para ver los comandos.")
        while True:
            try:
                line = input("wallet> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not line:
                continue
            parts = line.split()
            command = parts[0].lower()
            try:
                if command in {"quit", "exit"}:
                    return 0
                if command == "help":
                    print(self._HELP)
                elif command == "balance":
                    if len(parts) != 2:
                        print("Uso: balance <address>")
                        continue
                    balance = self._client.get_balance(parts[1])
                    print(f"balance {parts[1]}: {balance}")
                elif command == "transactions":
                    address = None
                    limit = 50
                    if len(parts) == 2:
                        if parts[1].isdigit():
                            limit = int(parts[1])
                        else:
                            address = parts[1]
                    elif len(parts) >= 3:
                        address = parts[1]
                        limit = int(parts[2])
                    txs = self._client.get_transactions(address, limit)
                    if not txs:
                        print("(sin transacciones)")
                    for tx in txs:
                        print(
                            f"{tx.id[:12]}... {tx.sender_id[:12]}... -> "
                            f"{tx.receiver_id[:12]}... amount={tx.amount}"
                        )
                elif command == "status":
                    status = self._client.get_status()
                    print(
                        f"node_id={status.get('node_id')} height={status.get('height')} "
                        f"difficulty={status.get('difficulty')} mempool={status.get('mempool_size')} "
                        f"peers={status.get('peers_connected')}"
                    )
                elif command == "accounts":
                    accounts = self._key_store.load_accounts()
                    if not accounts:
                        print("(sin cuentas locales)")
                    for account in accounts:
                        print(account.id)
                elif command == "create":
                    account = self._key_store.create_account()
                    print(f"Cuenta creada: {account.id}")
                elif command == "send":
                    if len(parts) != 4:
                        print("Uso: send <from> <to> <amount>")
                        continue
                    sender_id, receiver_id, amount_str = parts[1], parts[2], parts[3]
                    if not amount_str.isdigit():
                        print("El monto debe ser un entero positivo")
                        continue
                    amount = int(amount_str)
                    if amount <= 0:
                        print("El monto debe ser mayor que cero")
                        continue
                    sender = self._find_account(sender_id)
                    if sender is None:
                        print("No se encontró la cuenta emisora en keys_dir")
                        continue
                    balance = self._client.get_balance(sender.id)
                    if amount > balance:
                        print(f"Saldo insuficiente: {balance}")
                        continue
                    tx = build_signed_transaction(sender, receiver_id, amount)
                    if self._client.submit_transaction(tx):
                        print(f"Transacción aceptada: {tx.id}")
                    else:
                        print("El nodo rechazó la transacción")
                else:
                    print(f"Comando desconocido: {command}. Escriba 'help'.")
            except Exception as exc:
                print(f"Error: {exc}")

    def _find_account(self, address: str):
        for account in self._key_store.load_accounts():
            if account.id == address:
                return account
        return None
