"""Interfaz: validación de un bloque (estructura, PoW y transacciones)."""

from abc import ABC, abstractmethod

from main.domain.models.block import Block


class IBlockValidator(ABC):
    """Contrato para validar un bloque antes de añadirlo a la cadena."""

    @abstractmethod
    def validate(self, block: Block, previous_hash: str) -> bool:
        """Devuelve True si y solo si:

        1. `block.last_hash` == `previous_hash`.
        2. `block.hash` es el hash correcto del bloque (re-calculado) y cumple `block.target` (PoW).
        3. `block.transactions` contiene exactamente UNA transacción de recompensa de minado
           (sender_id == 'COINBASE') con amount igual al `mining_reward` configurado.
        4. Cada transacción no-coinbase es válida según ITransactionValidator (firma + reglas).
        5. `block.timestamp` > timestamp del bloque previo.
        """
        ...
