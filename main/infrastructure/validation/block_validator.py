"""Adaptador: validación de bloques (hash, PoW, transacciones). Ver doc/protocolo.md §5.3."""

from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.proof_of_work import IProofOfWork
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.domain.models.block import Block


class DefaultBlockValidator(IBlockValidator):
    """Implementación de IBlockValidator.

    Dependencias inyectadas para poder validar el bloque completo:
    - proof_of_work: recálculo de hash y verificación del PoW.
    - transaction_validator: validez de cada tx no-coinbase.
    - expected_difficulty: target esperado de la red (`block.target` debe coincidir).
    - mining_reward: amount esperado de la única tx coinbase del bloque.
    """

    def __init__(
        self,
        proof_of_work: IProofOfWork,
        transaction_validator: ITransactionValidator,
        expected_difficulty: int,
        mining_reward: int,
    ) -> None:
        self._proof_of_work = proof_of_work
        self._transaction_validator = transaction_validator
        self._expected_difficulty = expected_difficulty
        self._mining_reward = mining_reward

    def validate(self, block: Block, previous_hash: str) -> bool:
        raise NotImplementedError
