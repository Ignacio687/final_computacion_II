"""Gestión de claves de la billetera.

Responsabilidades:
- Crear/cargar pares de claves de usuario (PEM) en `keys_dir`.
- Derivar la dirección de una clave pública (sha256(DER), ver doc/protocolo.md §2.1).
- Derivar de forma determinista las cuentas pre-fondeadas del génesis a partir de la
  semilla compartida (doc/protocolo.md §8), para que el generador pueda gastar esos fondos.
"""

import hashlib
import os
from typing import List

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.domain.models.wallet_account import WalletAccount
from main.infrastructure.serialization.canonical import derive_sender_id


class KeyStore:
    """Crea, persiste y deriva identidades (WalletAccount) de la billetera."""

    def __init__(self, keys_dir: str) -> None:
        self._keys_dir = keys_dir

    def create_account(self) -> WalletAccount:
        """Genera un par de claves nuevo, lo persiste en `keys_dir` y devuelve la cuenta."""
        os.makedirs(self._keys_dir, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        account = self._account_from_private_key(private_key)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        path = os.path.join(self._keys_dir, f"{account.id}.pem")
        with open(path, "wb") as key_file:
            key_file.write(pem)
        return account

    def load_accounts(self) -> List[WalletAccount]:
        """Carga todas las cuentas (PEM) presentes en `keys_dir`."""
        if not os.path.isdir(self._keys_dir):
            return []
        accounts: List[WalletAccount] = []
        for name in sorted(os.listdir(self._keys_dir)):
            if not name.endswith(".pem"):
                continue
            path = os.path.join(self._keys_dir, name)
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as key_file:
                key = serialization.load_pem_private_key(key_file.read(), password=None)
            if not isinstance(key, Ed25519PrivateKey):
                continue
            accounts.append(self._account_from_private_key(key))
        return accounts

    @staticmethod
    def derive_genesis_accounts(genesis_seed: str, count: int) -> List[WalletAccount]:
        """Deriva de forma determinista las `count` cuentas pre-fondeadas del génesis a
        partir de `genesis_seed`, con EL MISMO algoritmo que SeedGenesisProvider
        (doc/protocolo.md §8): para i en 0..count-1,
            priv_seed_i = sha256(f"{genesis_seed}|prefund|{i}").digest()
            priv_i      = Ed25519PrivateKey.from_private_bytes(priv_seed_i)
            address_i   = sha256(public_key_DER_i).hexdigest()
        Permite al generador firmar transacciones con saldo inicial garantizado."""
        accounts: List[WalletAccount] = []
        for index in range(count):
            priv_seed = hashlib.sha256(
                f"{genesis_seed}|prefund|{index}".encode("utf-8")
            ).digest()
            private_key = Ed25519PrivateKey.from_private_bytes(priv_seed)
            accounts.append(KeyStore._account_from_private_key(private_key))
        return accounts

    @staticmethod
    def _account_from_private_key(private_key: Ed25519PrivateKey) -> WalletAccount:
        public_key_der = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        address = derive_sender_id(public_key_der)
        private_key_raw = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return WalletAccount(
            id=address,
            public_key=public_key_der,
            private_key=private_key_raw,
        )
