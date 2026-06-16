"""Consola interactiva de la billetera (modo no-generador).

Permite por línea de comandos consultar y operar contra un nodo vía WalletClient:
- ver balance de una dirección,
- listar transacciones,
- ver estado del nodo,
- crear/seleccionar una cuenta y enviar una transacción manual.
"""

import sys
import time

from main.wallet.wallet_client import WalletClient
from main.wallet.key_store import KeyStore
from main.wallet.tx_builder import build_signed_transaction
from main.wallet.status_display import (
    ANSI_CLEAR_SCREEN,
    collect_status_accounts,
    format_status_output,
    parse_status_args,
)


class WalletConsole:
    """Bucle de consola que traduce comandos del usuario a llamadas de WalletClient."""

    _HELP = (
        "Comandos:\n"
        "  help                              muestra esta ayuda\n"
        "  balance <address>                 consulta el saldo de una dirección\n"
        "  transactions [address] [limit]    lista transacciones confirmadas\n"
        "  status [live|once] [--interval N] estado del nodo y cuentas (live por defecto)\n"
        "  accounts                          lista cuentas locales\n"
        "  create                            crea una cuenta nueva\n"
        "  send <from> <to> <amount>         envía una transacción firmada\n"
        "  quit | exit                       sale de la consola"
    )

    def __init__(
        self,
        client: WalletClient,
        key_store: KeyStore,
        *,
        genesis_seed: str = "",
        genesis_prefund_accounts: int = 0,
        status_interval_seconds: float = 5.0,
    ) -> None:
        self._client = client
        self._key_store = key_store
        self._genesis_seed = (genesis_seed or "").strip()
        self._genesis_prefund_accounts = genesis_prefund_accounts
        self._status_interval_seconds = status_interval_seconds

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
                    try:
                        mode, interval = parse_status_args(
                            parts, self._status_interval_seconds
                        )
                    except ValueError as exc:
                        print(exc)
                        continue
                    if mode == "once":
                        self._print_status_snapshot(clear=False, interval_seconds=None)
                    else:
                        self._run_status_live(interval)
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

    def _genesis_accounts(self):
        if not self._genesis_seed or self._genesis_prefund_accounts <= 0:
            return []
        return KeyStore.derive_genesis_accounts(
            self._genesis_seed, self._genesis_prefund_accounts
        )

    def _status_account_rows(self):
        return collect_status_accounts(
            self._key_store.load_accounts(),
            self._genesis_accounts(),
            balance_lookup=self._client.get_balance,
        )

    def _print_status_snapshot(
        self,
        *,
        clear: bool,
        interval_seconds: float | None,
    ) -> None:
        status = self._client.get_status()
        accounts = self._status_account_rows()
        live = interval_seconds is not None
        output = format_status_output(
            status,
            accounts,
            live=live,
            interval_seconds=interval_seconds,
        )
        if clear:
            sys.stdout.write(ANSI_CLEAR_SCREEN)
        print(output, flush=True)

    def _run_status_live(self, interval_seconds: float) -> None:
        try:
            while True:
                self._print_status_snapshot(
                    clear=True,
                    interval_seconds=interval_seconds,
                )
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print()

    def _find_account(self, address: str):
        for account in self._key_store.load_accounts():
            if account.id == address:
                return account
        return None
