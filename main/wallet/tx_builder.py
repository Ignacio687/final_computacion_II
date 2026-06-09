"""Construcción y firma de transacciones del lado de la billetera.

Aplica el contrato canónico (doc/protocolo.md §3): arma los bytes firmables, firma con la
clave privada del usuario y calcula el id. Es la contraparte de la validación que hace el
nodo, de modo que toda transacción construida aquí es verificable allá.
"""

from main.domain.models.wallet_account import WalletAccount
from main.domain.models.transaction import Transaction


def build_signed_transaction(
    sender: WalletAccount,
    receiver_id: str,
    amount: int,
) -> Transaction:
    """Crea una Transaction firmada por `sender`:

    1. firmable = json_canonico({sender_id, receiver_id, amount})
    2. signature = sign(sender.private_key, firmable)
    3. id = sha256(firmable + signature)
    """
    raise NotImplementedError
