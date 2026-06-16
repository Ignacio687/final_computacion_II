"""Interfaz: validación de una transacción individual."""

from abc import ABC, abstractmethod

from main.domain.models.transaction import Transaction


class ITransactionValidator(ABC):
    """Contrato para validar una transacción antes de aceptarla en mempool."""

    @abstractmethod
    def validate(self, tx: Transaction) -> bool:
        """Devuelve True si y solo si la transacción cumple TODOS estos criterios:

        1. Firma criptográfica válida: `signature` corresponde a la serialización canónica
           de los campos firmables (id, sender_id, receiver_id, amount) verificada con `public_key`.
        2. `public_key` corresponde a `sender_id` (el id se deriva de la public_key).
        3. `id`, `sender_id`, `receiver_id` no vacíos; `sender_id` != `receiver_id`.
        4. `amount` > 0.
        5. Saldo del sender en la cadena confirmada >= `amount` (NO se considera el mempool).
        6. La transacción no existe ya en mempool ni en la cadena confirmada.
        """
        ...
