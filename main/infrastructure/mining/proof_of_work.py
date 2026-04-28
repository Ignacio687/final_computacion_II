"""Adaptador: PoW con SHA-256."""

from main.application.interfaces.proof_of_work import IProofOfWork, MiningResult
from main.domain.models.block import Block


class SHA256ProofOfWork(IProofOfWork):
    """Implementación de IProofOfWork. La dificultad viene en cada bloque (block.target)
    como cantidad de ceros hex iniciales requeridos en el hash."""

    def mine(self, block_candidate: Block) -> MiningResult:
        raise NotImplementedError

    def verify(self, block: Block) -> bool:
        raise NotImplementedError
