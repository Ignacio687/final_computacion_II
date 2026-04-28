"""Entidad transacción. Solo declaración de atributos."""

from dataclasses import dataclass


@dataclass(frozen=False)
class Transaction:
    """Transacción firmada. id, sender_id, receiver_id, amount (entero), signature, public_key."""

    id: str
    sender_id: str
    receiver_id: str
    amount: int
    signature: bytes
    public_key: bytes
