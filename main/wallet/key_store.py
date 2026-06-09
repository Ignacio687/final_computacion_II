"""Gestión de claves de la billetera.

Responsabilidades:
- Crear/cargar pares de claves de usuario (PEM) en `keys_dir`.
- Derivar la dirección de una clave pública (sha256(DER), ver doc/protocolo.md §2.1).
- Derivar de forma determinista las cuentas pre-fondeadas del génesis a partir de la
  semilla compartida (doc/protocolo.md §8), para que el generador pueda gastar esos fondos.
"""

from typing import List

from main.domain.models.wallet_account import WalletAccount


class KeyStore:
    """Crea, persiste y deriva identidades (WalletAccount) de la billetera."""

    def __init__(self, keys_dir: str) -> None:
        self._keys_dir = keys_dir

    def create_account(self) -> WalletAccount:
        """Genera un par de claves nuevo, lo persiste en `keys_dir` y devuelve la cuenta."""
        raise NotImplementedError

    def load_accounts(self) -> List[WalletAccount]:
        """Carga todas las cuentas (PEM) presentes en `keys_dir`."""
        raise NotImplementedError

    @staticmethod
    def derive_genesis_accounts(genesis_seed: str, count: int) -> List[WalletAccount]:
        """Deriva de forma determinista las `count` cuentas pre-fondeadas del génesis a
        partir de `genesis_seed`, con EL MISMO algoritmo que SeedGenesisProvider
        (doc/protocolo.md §8): para i en 0..count-1,
            priv_seed_i = sha256(f"{genesis_seed}|prefund|{i}").digest()
            priv_i      = Ed25519PrivateKey.from_private_bytes(priv_seed_i)
            address_i   = sha256(public_key_DER_i).hexdigest()
        Permite al generador firmar transacciones con saldo inicial garantizado."""
        raise NotImplementedError
