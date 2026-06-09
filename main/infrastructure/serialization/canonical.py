"""Utilidades canónicas de serialización y hashing (doc/protocolo.md §1-§5)."""

import base64
import hashlib
import json


def json_canonical(obj: object) -> bytes:
    """JSON canónico UTF-8: claves ordenadas, separadores mínimos."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """SHA-256 en hex minúsculas (64 caracteres)."""
    return hashlib.sha256(data).hexdigest()


def bytes_to_b64(data: bytes) -> str:
    """Codifica bytes a base64 estándar (RFC 4648, sin saltos de línea)."""
    return base64.b64encode(data).decode("ascii")


def b64_to_bytes(data: str) -> bytes:
    """Decodifica base64 estándar a bytes."""
    return base64.b64decode(data)


def derive_sender_id(public_key_der: bytes) -> str:
    """Dirección de usuario = sha256(public_key_DER) en hex (§2.1)."""
    return sha256_hex(public_key_der)


def transaction_firmable_bytes(sender_id: str, receiver_id: str, amount: int) -> bytes:
    """Bytes firmables de una transacción (§3.1)."""
    return json_canonical(
        {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "amount": amount,
        }
    )


def transaction_id(firmable: bytes, signature: bytes) -> str:
    """Id de transacción = sha256(firmable + signature) en hex (§3.2)."""
    return sha256_hex(firmable + signature)


def coinbase_id(height: int, mining_address: str, mining_reward: int) -> str:
    """Id de transacción coinbase (§4.1)."""
    return sha256_hex(
        f"COINBASE|{height}|{mining_address}|{mining_reward}".encode("utf-8")
    )


def genesis_tx_id(index: int, address: str, prefund_amount: int) -> str:
    """Id de transacción de fondeo génesis (§4.2 / §8)."""
    return sha256_hex(
        f"GENESIS|{index}|{address}|{prefund_amount}".encode("utf-8")
    )


def block_hasheable(
    last_hash: str,
    timestamp_epoch: float,
    target: int,
    nonce: int,
    transaction_ids: list[str],
) -> str:
    """Cadena hasheable de un bloque (§5.1)."""
    return "|".join(
        [
            last_hash,
            repr(timestamp_epoch),
            str(target),
            str(nonce),
            ",".join(transaction_ids),
        ]
    )


def block_hash(
    last_hash: str,
    timestamp_epoch: float,
    target: int,
    nonce: int,
    transaction_ids: list[str],
) -> str:
    """Hash PoW de un bloque (§5.1)."""
    hasheable = block_hasheable(
        last_hash, timestamp_epoch, target, nonce, transaction_ids
    )
    return sha256_hex(hasheable.encode("utf-8"))
