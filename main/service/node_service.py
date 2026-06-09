"""Orquestador del ciclo de vida del nodo."""

import asyncio

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.genesis_provider import IGenesisProvider
from main.application.interfaces.message_receiver import IMessageReceiver
from main.application.interfaces.message_sender import IMessageSender
from main.infrastructure.http.http_server import HTTPServer
from main.infrastructure.validation.chain_verification_dispatcher import (
    ChainVerificationDispatcher,
)
from main.service.mining_service import MiningService
from main.service.propagation_service import PropagationService


class NodeService:
    """Coordina arranque y parada."""

    def __init__(
        self,
        message_sender: IMessageSender,
        message_receiver: IMessageReceiver,
        blockchain_repository: IBlockchainRepository,
        genesis_provider: IGenesisProvider,
        http_server: HTTPServer,
        propagation_service: PropagationService,
        mining_service: MiningService,
        chain_dispatcher: ChainVerificationDispatcher,
    ) -> None:
        self._message_sender = message_sender
        self._message_receiver = message_receiver
        self._blockchain_repository = blockchain_repository
        self._genesis_provider = genesis_provider
        self._http_server = http_server
        self._propagation_service = propagation_service
        self._mining_service = mining_service
        self._chain_dispatcher = chain_dispatcher
        self._stop_event = asyncio.Event()
        self._mining_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._blockchain_repository.get_last_block() is None:
            self._blockchain_repository.append_block(
                self._genesis_provider.get_genesis_block()
            )
        self._chain_dispatcher.start()
        await self._message_receiver.start()
        await self._message_sender.start()
        await self._http_server.start()
        self._mining_task = asyncio.create_task(self._mining_service.start_loop())
        await self._stop_event.wait()

    async def stop(self) -> None:
        self._stop_event.set()
        await self._mining_service.stop_loop()
        if self._mining_task is not None:
            self._mining_task.cancel()
            await asyncio.gather(self._mining_task, return_exceptions=True)
            self._mining_task = None
        await self._http_server.stop()
        await self._message_sender.stop()
        await self._message_receiver.stop()
        self._chain_dispatcher.stop()
