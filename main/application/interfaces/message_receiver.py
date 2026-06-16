"""Interfaz: servidor TCP que recibe mensajes y los entrega al handler registrado."""

from abc import ABC, abstractmethod
from typing import Callable, Awaitable

from main.domain.models.message import Message
from main.domain.models.node_info import NodeInfo


# Tipo del callback que procesa cada mensaje recibido (peer, message) -> coroutine.
MessageHandler = Callable[[NodeInfo, Message], Awaitable[None]]


class IMessageReceiver(ABC):
    """Contrato para el servidor TCP del nodo."""

    @abstractmethod
    def set_handler(self, handler: MessageHandler) -> None:
        """Registra el callback que se invoca por cada mensaje recibido. Debe llamarse
        antes de start()."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Inicia el servidor TCP (bind, listen, accept loop). No retorna hasta que se llama stop()."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Detiene el servidor y cierra las conexiones entrantes."""
        ...
