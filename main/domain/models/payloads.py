"""Payloads tipados del protocolo TCP entre nodos.

Cada MessageType tiene UN payload concreto. Mapeo obligatorio (sin excepciones):
    HELLO             -> HelloPayload
    NEW_TX            -> NewTxPayload
    NEW_BLOCK         -> NewBlockPayload
    GET_CHAIN         -> GetChainPayload
    CHAIN_RESPONSE    -> ChainResponsePayload
    GET_MEMPOOL       -> GetMempoolPayload
    MEMPOOL_RESPONSE  -> MempoolResponsePayload
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union

from main.repository.dto.block_dto import BlockDTO
from main.repository.dto.transaction_dto import TransactionDTO


@dataclass(frozen=True)
class HelloPayload:
    """Payload de HELLO (handshake, ver doc/protocolo.md §6.5).

    - node_id: identificador del nodo emisor.
    - public_key: clave pública del nodo en base64 (DER). El receptor la registra para
      verificar las firmas de los próximos mensajes de ese node_id (TOFU).
    - listen_port: puerto TCP donde el emisor acepta conexiones (para reconectar)."""

    node_id: str
    public_key: str
    listen_port: int


@dataclass(frozen=True)
class NewTxPayload:
    """Payload de NEW_TX. Una transacción a propagar."""

    transaction: TransactionDTO


@dataclass(frozen=True)
class NewBlockPayload:
    """Payload de NEW_BLOCK. Bloque completo (con todas sus transacciones) a propagar."""

    block: BlockDTO


@dataclass(frozen=True)
class GetChainPayload:
    """Payload de GET_CHAIN. Pide bloques desde la altura indicada (0 = cadena completa)."""

    since_height: int


@dataclass(frozen=True)
class ChainResponsePayload:
    """Payload de CHAIN_RESPONSE. Bloques desde la altura solicitada, en orden ascendente."""

    blocks: List[BlockDTO]


@dataclass(frozen=True)
class GetMempoolPayload:
    """Payload de GET_MEMPOOL. Sin campos."""

    pass


@dataclass(frozen=True)
class MempoolResponsePayload:
    """Payload de MEMPOOL_RESPONSE. Lista completa del mempool del peer."""

    transactions: List[TransactionDTO]


MessagePayload = Union[
    HelloPayload,
    NewTxPayload,
    NewBlockPayload,
    GetChainPayload,
    ChainResponsePayload,
    GetMempoolPayload,
    MempoolResponsePayload,
]
