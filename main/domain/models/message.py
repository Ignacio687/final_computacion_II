"""Mensaje del protocolo TCP entre nodos: tipo + payload tipado."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass

from main.domain.models.payloads import MessagePayload


class MessageType(str, Enum):
    """Tipos de mensaje del protocolo. El tipo determina la clase concreta del payload (ver payloads.py)."""

    NEW_TX = "NEW_TX"
    NEW_BLOCK = "NEW_BLOCK"
    GET_CHAIN = "GET_CHAIN"
    CHAIN_RESPONSE = "CHAIN_RESPONSE"
    GET_MEMPOOL = "GET_MEMPOOL"
    MEMPOOL_RESPONSE = "MEMPOOL_RESPONSE"
    PING = "PING"
    PONG = "PONG"


@dataclass(frozen=False)
class Message:
    """Mensaje del protocolo. payload es uno de los dataclasses definidos en payloads.py
    según el mapeo MessageType -> Payload."""

    type: MessageType
    payload: MessagePayload
