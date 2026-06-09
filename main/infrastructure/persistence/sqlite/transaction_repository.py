"""Adaptador: persistencia de transacciones (mempool y confirmadas) en SQLite."""

import sqlite3
import threading
from typing import List

from main.application.interfaces.transaction_repository import ITransactionRepository
from main.domain.models.transaction import Transaction
from main.infrastructure.persistence.sqlite.blockchain_repository import (
    _connect,
    _transaction_from_row,
    ensure_schema,
)
from main.repository.dto.mappers import transaction_to_dto


class SQLiteTransactionRepository(ITransactionRepository):
    """Implementación de ITransactionRepository usando SQLite (esquema canónico en
    doc/protocolo.md §11: tablas `mempool` y `transactions`). db_path es el mismo archivo
    que usa SQLiteBlockchainRepository. Las consultas de balance/historial se calculan solo
    sobre `transactions` (confirmadas), nunca sobre `mempool`."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        ensure_schema(db_path)

    def add_to_mempool(self, tx: Transaction) -> None:
        dto = transaction_to_dto(tx)
        with self._lock:
            with _connect(self._db_path) as conn:
                row = conn.execute("SELECT COALESCE(MAX(seq), -1) + 1 FROM mempool").fetchone()
                seq = row[0]
                conn.execute(
                    "INSERT INTO mempool "
                    "(id, seq, sender_id, receiver_id, amount, signature, public_key) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        dto.id,
                        seq,
                        dto.sender_id,
                        dto.receiver_id,
                        dto.amount,
                        dto.signature,
                        dto.public_key,
                    ),
                )
                conn.commit()

    def get_mempool(self) -> List[Transaction]:
        with self._lock:
            with _connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT id, sender_id, receiver_id, amount, signature, public_key "
                    "FROM mempool ORDER BY seq ASC"
                ).fetchall()
                return [_transaction_from_row(row) for row in rows]

    def remove_from_mempool(self, tx_ids: List[str]) -> None:
        if not tx_ids:
            return
        with self._lock:
            with _connect(self._db_path) as conn:
                placeholders = ",".join("?" for _ in tx_ids)
                conn.execute(
                    f"DELETE FROM mempool WHERE id IN ({placeholders})",
                    tx_ids,
                )
                conn.commit()

    def exists_in_mempool_or_chain(self, tx_id: str) -> bool:
        with self._lock:
            with _connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT 1 FROM mempool WHERE id = ? "
                    "UNION SELECT 1 FROM transactions WHERE id = ? LIMIT 1",
                    (tx_id, tx_id),
                ).fetchone()
                return row is not None

    def get_balance(self, address: str) -> int:
        with self._lock:
            with _connect(self._db_path) as conn:
                received = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE receiver_id = ?",
                    (address,),
                ).fetchone()[0]
                sent = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE sender_id = ?",
                    (address,),
                ).fetchone()[0]
                return int(received) - int(sent)

    def get_transactions_for_address(self, address: str, limit: int) -> List[Transaction]:
        with self._lock:
            with _connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT t.id, t.sender_id, t.receiver_id, t.amount, t.signature, t.public_key "
                    "FROM transactions t "
                    "JOIN blocks b ON t.block_id = b.id "
                    "WHERE t.sender_id = ? OR t.receiver_id = ? "
                    "ORDER BY b.id DESC, t.position DESC "
                    "LIMIT ?",
                    (address, address, limit),
                ).fetchall()
                return [_transaction_from_row(row) for row in rows]

    def get_recent_transactions(self, limit: int) -> List[Transaction]:
        with self._lock:
            with _connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT t.id, t.sender_id, t.receiver_id, t.amount, t.signature, t.public_key "
                    "FROM transactions t "
                    "JOIN blocks b ON t.block_id = b.id "
                    "ORDER BY b.id DESC, t.position DESC "
                    "LIMIT ?",
                    (limit,),
                ).fetchall()
                return [_transaction_from_row(row) for row in rows]
