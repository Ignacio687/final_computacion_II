"""Handler de mensajes TCP: recibe (peer, message) y delega en PropagationService."""

from main.domain.models.message import Message
from main.domain.models.node_info import NodeInfo
from main.service.propagation_service import PropagationService


class TCPMessageHandler:
    """Conecta IMessageReceiver con PropagationService.handle_message."""

    def __init__(self, propagation_service: PropagationService) -> None:
        self._propagation_service = propagation_service

    async def handle(self, peer: NodeInfo, message: Message) -> None:
        await self._propagation_service.handle_message(peer, message)
