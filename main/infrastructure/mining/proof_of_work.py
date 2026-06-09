"""Adaptador: PoW con SHA-256."""

from main.application.interfaces.proof_of_work import IProofOfWork, MiningResult
from main.domain.models.block import Block
from main.infrastructure.serialization.canonical import block_hash

COINBASE_SENDER = "COINBASE"
GENESIS_SENDER = "GENESIS"


class SHA256ProofOfWork(IProofOfWork):
    """Implementación de IProofOfWork. La dificultad viene en cada bloque (block.target)
    como cantidad de ceros hex iniciales requeridos en el hash."""

    def mine(self, block_candidate: Block) -> MiningResult:
        tx_ids = [tx.id for tx in block_candidate.transactions]
        timestamp_epoch = block_candidate.timestamp.timestamp()
        prefix = "0" * block_candidate.target
        nonce = 0
        while True:
            computed = block_hash(
                block_candidate.last_hash,
                timestamp_epoch,
                block_candidate.target,
                nonce,
                tx_ids,
            )
            if computed.startswith(prefix):
                return MiningResult(nonce=nonce, block_hash=computed)
            nonce += 1

    def verify(self, block: Block) -> bool:
        tx_ids = [tx.id for tx in block.transactions]
        timestamp_epoch = block.timestamp.timestamp()
        computed = block_hash(
            block.last_hash,
            timestamp_epoch,
            block.target,
            block.nonce,
            tx_ids,
        )
        if computed != block.hash:
            return False
        return block.hash.startswith("0" * block.target)
