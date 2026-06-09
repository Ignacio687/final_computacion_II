"""Entidad transacción. Solo declaración de atributos."""

from dataclasses import dataclass


@dataclass(frozen=False)
class Transaction:
    """Transacción firmada. Ver contrato canónico en doc/protocolo.md §3 y §4.

    - sender_id / receiver_id: direcciones = sha256(public_key_DER) en hex. Valores
      reservados sin firma: "COINBASE" (recompensa) y "GENESIS" (fondeo inicial).
    - amount: entero positivo.
    - signature: firma sobre los bytes firmables = json_canonico({sender_id, receiver_id,
      amount}). Vacía (b"") para coinbase/génesis.
    - public_key: clave pública DER del emisor. Vacía (b"") para coinbase/génesis.
    - id: sha256(firmable + signature) en hex. Para coinbase/génesis se deriva según §4.
    """

    id: str
    sender_id: str
    receiver_id: str
    amount: int
    signature: bytes
    public_key: bytes
