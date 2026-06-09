"""Mappers DTO <-> dominio.

Convierten entre las entidades del dominio (Transaction, Block) y sus DTO serializables.
Encapsulan las codificaciones del protocolo (base64 de bytes, epoch <-> datetime); ver
doc/protocolo.md §1 y §3-§5. Los usan tanto la red (codec TCP) como la persistencia SQLite.
"""

from main.domain.models.transaction import Transaction
from main.domain.models.block import Block
from main.repository.dto.transaction_dto import TransactionDTO
from main.repository.dto.block_dto import BlockDTO


def transaction_to_dto(tx: Transaction) -> TransactionDTO:
    """Domain -> DTO. signature/public_key a base64."""
    raise NotImplementedError


def transaction_from_dto(dto: TransactionDTO) -> Transaction:
    """DTO -> domain. signature/public_key desde base64."""
    raise NotImplementedError


def block_to_dto(block: Block) -> BlockDTO:
    """Domain -> DTO. timestamp (datetime) -> epoch float; transacciones mapeadas."""
    raise NotImplementedError


def block_from_dto(dto: BlockDTO) -> Block:
    """DTO -> domain. epoch float -> datetime UTC; transacciones mapeadas."""
    raise NotImplementedError
