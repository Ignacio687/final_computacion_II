"""DTO serializable de Transaction para JSON sobre TCP y persistencia SQLite.

Codificaciones obligatorias:
    - signature: base64 (RFC 4648, sin saltos de línea)
    - public_key: base64 (RFC 4648, sin saltos de línea)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionDTO:
    """Representación serializable de una transacción."""

    id: str
    sender_id: str
    receiver_id: str
    amount: int
    signature: str
    public_key: str
