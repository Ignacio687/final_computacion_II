"""Servicio de minado: arma bloque candidato, ejecuta PoW en ProcessPoolExecutor."""

import asyncio
from concurrent.futures import Executor
from datetime import datetime, timezone

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.proof_of_work import IProofOfWork
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.domain.models.block import Block
from main.domain.models.message import Message, MessageType
from main.domain.models.payloads import NewBlockPayload
from main.domain.models.transaction import Transaction
from main.infrastructure.serialization.canonical import coinbase_id
from main.repository.dto.mappers import block_to_dto


class MiningService:
    """Minado periódico con ProcessPoolExecutor."""

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
        self._last_attempt: float | None = None
        self._running = False
        self._task: asyncio.Task | None = None

    async def try_mine(self) -> None:
        now = asyncio.get_running_loop().time()
        mempool = self._transaction_repository.get_mempool()
        interval_elapsed = (
            self._last_attempt is None
            or now - self._last_attempt >= self._block_interval_seconds
        )
        enough_txs = len(mempool) >= self._min_transactions_per_block
        if not interval_elapsed and not enough_txs:
            return
        self._last_attempt = now

        last_block = self._blockchain_repository.get_last_block()
        if last_block is None:
            return

        block_id = last_block.id + 1
        coinbase = Transaction(
            id=coinbase_id(block_id, self._mining_address, self._mining_reward),
            sender_id="COINBASE",
            receiver_id=self._mining_address,
            amount=self._mining_reward,
            signature=b"",
            public_key=b"",
        )
        candidate = Block(
            id=block_id,
            last_hash=last_block.hash,
            hash="",
            timestamp=datetime.now(timezone.utc),
            target=self._difficulty,
            nonce=0,
            transactions=[coinbase, *mempool],
        )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(self._pool, self._proof_of_work.mine, candidate)
        candidate.nonce = result.nonce
        candidate.hash = result.block_hash

        self._blockchain_repository.append_block(candidate)
        tx_ids = [tx.id for tx in candidate.transactions]
        self._transaction_repository.remove_from_mempool(tx_ids)
        await self._message_sender.broadcast(
            Message(
                type=MessageType.NEW_BLOCK,
                payload=NewBlockPayload(block=block_to_dto(candidate)),
            )
        )

    async def start_loop(self) -> None:
        self._running = True
        while self._running:
            try:
                await self.try_mine()
            except Exception:
                pass
            await asyncio.sleep(1.0)

    async def stop_loop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
