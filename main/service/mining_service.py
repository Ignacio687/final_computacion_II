"""Servicio de minado: arma bloque candidato, ejecuta PoW en ProcessPoolExecutor,
persiste el bloque y lo propaga (NEW_BLOCK)."""

from concurrent.futures import Executor

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.proof_of_work import IProofOfWork
from main.application.interfaces.message_sender import IMessageSender


class MiningService:
    """Reglas de minado (ensamblado canónico en doc/protocolo.md §5.0 y coinbase §4.1):

    Cada vez que el mempool tiene >= `min_transactions_per_block` o pasaron
    `block_interval_seconds` desde el último intento, arma un bloque candidato:
        - id = get_last_block().id + 1; last_hash = get_last_block().hash; target = difficulty.
        - transactions = [coinbase] + mempool (coinbase PRIMERO; resto en orden de inserción).
    Ejecuta el PoW en el ProcessPoolExecutor vía `loop.run_in_executor(pool, pow.mine,
    candidate)` (el bloque candidato y SHA256ProofOfWork son picklables: el método no tiene
    estado). Con el nonce/hash resultante: setea el bloque, lo añade a la cadena, elimina del
    mempool las tx incluidas y hace broadcast NEW_BLOCK a los peers.
    """

    def __init__(
        self,
        blockchain_repository: IBlockchainRepository,
        transaction_repository: ITransactionRepository,
        proof_of_work: IProofOfWork,
        message_sender: IMessageSender,
        pool: Executor,
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
        self._pool = pool
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
