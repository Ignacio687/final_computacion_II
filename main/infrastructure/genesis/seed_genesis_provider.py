"""Adaptador: bloque génesis derivado de una semilla string."""

import hashlib
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.application.interfaces.genesis_provider import IGenesisProvider
from main.domain.models.block import Block
from main.domain.models.transaction import Transaction
from main.infrastructure.serialization.canonical import (
    block_hash,
    derive_sender_id,
    genesis_tx_id,
)

GENESIS_SENDER = "GENESIS"


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
        transactions: list[Transaction] = []
        for index in range(self._prefund_accounts):
            priv_seed = hashlib.sha256(
                f"{self._seed}|prefund|{index}".encode("utf-8")
            ).digest()
            private_key = Ed25519PrivateKey.from_private_bytes(priv_seed)
            public_key_der = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            address = derive_sender_id(public_key_der)
            transactions.append(
                Transaction(
                    id=genesis_tx_id(index, address, self._prefund_amount),
                    sender_id=GENESIS_SENDER,
                    receiver_id=address,
                    amount=self._prefund_amount,
                    signature=b"",
                    public_key=b"",
                )
            )

        last_hash = "0" * 64
        timestamp_epoch = 0.0
        target = 0
        nonce = 0
        tx_ids = [tx.id for tx in transactions]
        block_hash_value = block_hash(
            last_hash, timestamp_epoch, target, nonce, tx_ids
        )

        return Block(
            id=0,
            last_hash=last_hash,
            hash=block_hash_value,
            timestamp=datetime.fromtimestamp(timestamp_epoch, tz=timezone.utc),
            target=target,
            nonce=nonce,
            transactions=transactions,
        )
