"""Servicio de minado: arma bloque candidato, ejecuta PoW en ProcessPoolExecutor,
persiste el bloque y lo propaga (NEW_BLOCK)."""

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.proof_of_work import IProofOfWork
from main.application.interfaces.message_sender import IMessageSender


class MiningService:
    """Reglas de minado:

    Cada vez que el mempool tiene >= `min_transactions_per_block` o pasaron
    `block_interval_seconds` desde el último intento, arma un bloque candidato con esas
    transacciones más una transacción de recompensa (sender 'COINBASE', receiver
    `mining_address`, amount `mining_reward`), ejecuta PoW en el ProcessPoolExecutor
    inyectado por el bootstrap, añade el bloque a la cadena, lo elimina del mempool y
    hace broadcast NEW_BLOCK.
    """

    def __init__(
        self,
        blockchain_repository: IBlockchainRepository,
        transaction_repository: ITransactionRepository,
        proof_of_work: IProofOfWork,
        message_sender: IMessageSender,
        difficulty: int,
        min_transactions_per_block: int,
        block_interval_seconds: float,
        mining_reward: int,
        mining_address: str,
    ) -> None:
        self._blockchain_repository = blockchain_repository
        self._transaction_repository = transaction_repository
        self._proof_of_work = proof_of_work
        self._message_sender = message_sender
        self._difficulty = difficulty
        self._min_transactions_per_block = min_transactions_per_block
        self._block_interval_seconds = block_interval_seconds
        self._mining_reward = mining_reward
        self._mining_address = mining_address

    async def try_mine(self) -> None:
        """Ejecuta una iteración de minado si se cumplen las condiciones (umbral o intervalo)."""
        raise NotImplementedError

    async def start_loop(self) -> None:
        """Inicia el loop asyncio que llama a try_mine periódicamente. Bloqueante hasta stop_loop."""
        raise NotImplementedError

    async def stop_loop(self) -> None:
        """Detiene el loop de minado."""
        raise NotImplementedError
