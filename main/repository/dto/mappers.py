"""Mappers DTO <-> dominio.

Convierten entre las entidades del dominio (Transaction, Block) y sus DTO serializables.
Encapsulan las codificaciones del protocolo (base64 de bytes, epoch <-> datetime); ver
doc/protocolo.md §1 y §3-§5. Los usan tanto la red (codec TCP) como la persistencia SQLite.
"""

from datetime import datetime, timezone

from main.domain.models.transaction import Transaction
from main.domain.models.block import Block
from main.infrastructure.serialization.canonical import b64_to_bytes, bytes_to_b64
from main.repository.dto.transaction_dto import TransactionDTO
from main.repository.dto.block_dto import BlockDTO


def transaction_to_dto(tx: Transaction) -> TransactionDTO:
    """Domain -> DTO. signature/public_key a base64."""
    return TransactionDTO(
        id=tx.id,
        sender_id=tx.sender_id,
        receiver_id=tx.receiver_id,
        amount=tx.amount,
        signature=bytes_to_b64(tx.signature),
        public_key=bytes_to_b64(tx.public_key),
    )


def transaction_from_dto(dto: TransactionDTO) -> Transaction:
    """DTO -> domain. signature/public_key desde base64."""
    return Transaction(
        id=dto.id,
        sender_id=dto.sender_id,
        receiver_id=dto.receiver_id,
        amount=dto.amount,
        signature=b64_to_bytes(dto.signature),
        public_key=b64_to_bytes(dto.public_key),
    )


def block_to_dto(block: Block) -> BlockDTO:
    """Domain -> DTO. timestamp (datetime) -> epoch float; transacciones mapeadas."""
    return BlockDTO(
        id=block.id,
        last_hash=block.last_hash,
        hash=block.hash,
        timestamp=block.timestamp.timestamp(),
        target=block.target,
        nonce=block.nonce,
        transactions=[transaction_to_dto(tx) for tx in block.transactions],
    )


def block_from_dto(dto: BlockDTO) -> Block:
    """DTO -> domain. epoch float -> datetime UTC; transacciones mapeadas."""
    return Block(
        id=dto.id,
        last_hash=dto.last_hash,
        hash=dto.hash,
        timestamp=datetime.fromtimestamp(dto.timestamp, tz=timezone.utc),
        target=dto.target,
        nonce=dto.nonce,
        transactions=[transaction_from_dto(tx) for tx in dto.transactions],
    )
