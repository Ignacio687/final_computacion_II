"""Adaptador: validación de bloques (hash, PoW)."""

from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.proof_of_work import IProofOfWork
from main.domain.models.block import Block


class DefaultBlockValidator(IBlockValidator):
    """Implementación de IBlockValidator; usa IProofOfWork para verificar nonce/hash."""

    def __init__(self, proof_of_work: IProofOfWork) -> None:
        self._proof_of_work = proof_of_work

    def validate(self, block: Block, previous_hash: str) -> bool:
        raise NotImplementedError
