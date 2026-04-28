"""Interfaz: envío de mensajes a peers por TCP (JSON cifrado/firmado)."""

from abc import ABC, abstractmethod

from main.domain.models.message import Message
from main.domain.models.node_info import NodeInfo


class IMessageSender(ABC):
    """Contrato para gestionar conexiones salientes a peers y enviar mensajes."""

    @abstractmethod
    async def start(self) -> None:
        """Abre conexiones TCP persistentes con todos los peers de la lista.
        Aplica reconexión con backoff exponencial ante caídas."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Cierra todas las conexiones salientes."""
        ...

    @abstractmethod
    async def send_to_peer(self, peer: NodeInfo, message: Message) -> None:
        """Envía el mensaje al peer indicado. Si la conexión está caída, encola y reintenta
        cuando se restablezca."""
        ...

    @abstractmethod
    async def broadcast(self, message: Message) -> None:
        """Envía el mensaje a todos los peers conectados."""
        ...
