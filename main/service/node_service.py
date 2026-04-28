"""Orquestador del ciclo de vida del nodo: arranca y detiene los componentes en orden."""

from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.message_receiver import IMessageReceiver
from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.genesis_provider import IGenesisProvider
from main.infrastructure.http.http_server import HTTPServer
from main.service.propagation_service import PropagationService
from main.service.mining_service import MiningService


class NodeService:
    """Coordina arranque y parada. NO contiene lógica de negocio.

    start():
      1. Si la cadena está vacía: append del bloque génesis (IGenesisProvider).
      2. propagation_service registra su handler en message_receiver.
      3. message_sender.start() (abre conexiones a peers).
      4. message_receiver.start() (acepta conexiones entrantes).
      5. http_server.start().
      6. mining_service.start_loop().

    stop(): inverso al start.
    """

    def __init__(
        self,
        message_sender: IMessageSender,
        message_receiver: IMessageReceiver,
        blockchain_repository: IBlockchainRepository,
        genesis_provider: IGenesisProvider,
        http_server: HTTPServer,
        propagation_service: PropagationService,
        mining_service: MiningService,
    ) -> None:
        self._message_sender = message_sender
        self._message_receiver = message_receiver
        self._blockchain_repository = blockchain_repository
        self._genesis_provider = genesis_provider
        self._http_server = http_server
        self._propagation_service = propagation_service
        self._mining_service = mining_service

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError
