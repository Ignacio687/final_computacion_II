"""Servicio de minado: arma bloque candidato, ejecuta PoW en ProcessPoolExecutor."""

import asyncio
import logging
import sqlite3
from concurrent.futures import Executor
from datetime import datetime, timezone

from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.proof_of_work import IProofOfWork
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.domain.models.block import Block
from main.domain.models.message import Message, MessageType
from main.domain.models.payloads import NewBlockPayload
from main.domain.models.transaction import Transaction
from main.infrastructure.serialization.canonical import coinbase_id
from main.infrastructure.validation.block_validator import (
    DefaultBlockValidator,
    balances_from_chain,
)
from main.repository.dto.mappers import block_to_dto

logger = logging.getLogger(__name__)


class MiningService:
    def __init__(
        self,
        blockchain_repository: IBlockchainRepository,
        transaction_repository: ITransactionRepository,
        proof_of_work: IProofOfWork,
        block_validator: IBlockValidator,
        message_sender: IMessageSender,
        pool: Executor,
        difficulty: int,
        min_transactions_per_block: int,
        block_interval_seconds: float,
        mining_reward: int,
        mining_address: str,
        chain_lock: asyncio.Lock,
    ) -> None:
        self._blockchain_repository = blockchain_repository
        self._transaction_repository = transaction_repository
        self._proof_of_work = proof_of_work
        self._block_validator = block_validator
        self._message_sender = message_sender
        self._pool = pool
        self._difficulty = difficulty
        self._min_transactions_per_block = min_transactions_per_block
        self._block_interval_seconds = block_interval_seconds
        self._mining_reward = mining_reward
        self._mining_address = mining_address
        self._chain_lock = chain_lock
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

        tip_id = last_block.id
        tip_hash = last_block.hash
        block_id = tip_id + 1
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
            last_hash=tip_hash,
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

        inserted = False
        async with self._chain_lock:
            tip = self._blockchain_repository.get_last_block()
            if tip is None or tip.id != tip_id or tip.hash != tip_hash:
                return
            if candidate.id != tip.id + 1 or candidate.last_hash != tip.hash:
                return
            if not self._is_candidate_valid(candidate, tip):
                return

            if not self._blockchain_repository.append_block(candidate):
                return
            inserted = True
            tx_ids = [tx.id for tx in candidate.transactions]
            self._transaction_repository.remove_from_mempool(tx_ids)

        if inserted:
            await self._message_sender.broadcast(
                Message(
                    type=MessageType.NEW_BLOCK,
                    payload=NewBlockPayload(block=block_to_dto(candidate)),
                )
            )

    def _is_candidate_valid(self, candidate: Block, tip: Block) -> bool:
        if isinstance(self._block_validator, DefaultBlockValidator):
            balances = balances_from_chain(self._blockchain_repository.get_chain())
            return self._block_validator.validate_with_balances(
                candidate,
                tip.hash,
                balances,
                previous_timestamp=tip.timestamp,
            )
        return self._block_validator.validate(candidate, tip.hash)

    async def start_loop(self) -> None:
        self._running = True
        while self._running:
            try:
                await self.try_mine()
            except sqlite3.IntegrityError:
                logger.warning("Bloque duplicado al minar; se descarta el candidato")
            except Exception:
                logger.exception("Error inesperado en el loop de minado")
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
