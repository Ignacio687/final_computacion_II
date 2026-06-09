"""Adaptador: persistencia de la blockchain en SQLite."""

import sqlite3
import threading
from typing import List

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.domain.models.block import Block
from main.domain.models.transaction import Transaction
from main.repository.dto.mappers import block_from_dto, block_to_dto, transaction_from_dto, transaction_to_dto
from main.repository.dto.block_dto import BlockDTO
from main.repository.dto.transaction_dto import TransactionDTO

_SCHEMA = """
CREATE TABLE IF NOT EXISTS blocks (
    id        INTEGER PRIMARY KEY,
    last_hash TEXT NOT NULL,
    hash      TEXT NOT NULL UNIQUE,
    timestamp REAL NOT NULL,
    target    INTEGER NOT NULL,
    nonce     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id          TEXT PRIMARY KEY,
    block_id    INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    sender_id   TEXT NOT NULL,
    receiver_id TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    signature   TEXT NOT NULL,
    public_key  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mempool (
    id          TEXT PRIMARY KEY,
    seq         INTEGER NOT NULL,
    sender_id   TEXT NOT NULL,
    receiver_id TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    signature   TEXT NOT NULL,
    public_key  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tx_sender   ON transactions(sender_id);
CREATE INDEX IF NOT EXISTS idx_tx_receiver ON transactions(receiver_id);
CREATE INDEX IF NOT EXISTS idx_tx_block    ON transactions(block_id);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(db_path: str) -> None:
    """Crea las tablas canónicas si no existen (§11)."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def _transaction_from_row(row: sqlite3.Row) -> Transaction:
    return transaction_from_dto(
        TransactionDTO(
            id=row["id"],
            sender_id=row["sender_id"],
            receiver_id=row["receiver_id"],
            amount=row["amount"],
            signature=row["signature"],
            public_key=row["public_key"],
        )
    )


def _load_block(conn: sqlite3.Connection, block_row: sqlite3.Row) -> Block:
    tx_rows = conn.execute(
        "SELECT id, sender_id, receiver_id, amount, signature, public_key "
        "FROM transactions WHERE block_id = ? ORDER BY position ASC",
        (block_row["id"],),
    ).fetchall()
    dto = BlockDTO(
        id=block_row["id"],
        last_hash=block_row["last_hash"],
        hash=block_row["hash"],
        timestamp=block_row["timestamp"],
        target=block_row["target"],
        nonce=block_row["nonce"],
        transactions=[
            TransactionDTO(
                id=row["id"],
                sender_id=row["sender_id"],
                receiver_id=row["receiver_id"],
                amount=row["amount"],
                signature=row["signature"],
                public_key=row["public_key"],
            )
            for row in tx_rows
        ],
    )
    return block_from_dto(dto)


def _insert_block(conn: sqlite3.Connection, block: Block) -> None:
    dto = block_to_dto(block)
    conn.execute(
        "INSERT INTO blocks (id, last_hash, hash, timestamp, target, nonce) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (dto.id, dto.last_hash, dto.hash, dto.timestamp, dto.target, dto.nonce),
    )
    for position, tx in enumerate(block.transactions):
        tx_dto = transaction_to_dto(tx)
        conn.execute(
            "INSERT INTO transactions "
            "(id, block_id, position, sender_id, receiver_id, amount, signature, public_key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tx_dto.id,
                dto.id,
                position,
                tx_dto.sender_id,
                tx_dto.receiver_id,
                tx_dto.amount,
                tx_dto.signature,
                tx_dto.public_key,
            ),
        )


class SQLiteBlockchainRepository(IBlockchainRepository):
    """Implementación de IBlockchainRepository usando SQLite. Crea las tablas si no existen
    al instanciarse (esquema canónico en doc/protocolo.md §11: tablas `blocks` y
    `transactions`). db_path es la ruta del archivo SQLite (un archivo por nodo).
    `append_block` persiste el bloque y sus tx (con `position`) y limpia del mempool las tx
    confirmadas; `replace_chain` reemplaza la cadena de forma atómica."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        ensure_schema(db_path)

    def get_chain(self) -> List[Block]:
        with self._lock:
            with _connect(self._db_path) as conn:
                rows = conn.execute("SELECT * FROM blocks ORDER BY id ASC").fetchall()
                return [_load_block(conn, row) for row in rows]

    def get_chain_since(self, height: int) -> List[Block]:
        with self._lock:
            with _connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT * FROM blocks WHERE id >= ? ORDER BY id ASC",
                    (height,),
                ).fetchall()
                return [_load_block(conn, row) for row in rows]

    def append_block(self, block: Block) -> None:
        tx_ids = [tx.id for tx in block.transactions]
        with self._lock:
            with _connect(self._db_path) as conn:
                _insert_block(conn, block)
                if tx_ids:
                    placeholders = ",".join("?" for _ in tx_ids)
                    conn.execute(
                        f"DELETE FROM mempool WHERE id IN ({placeholders})",
                        tx_ids,
                    )
                conn.commit()

    def replace_chain(self, blocks: List[Block]) -> None:
        new_confirmed_ids = {tx.id for block in blocks for tx in block.transactions}
        with self._lock:
            with _connect(self._db_path) as conn:
                old_tx_rows = conn.execute(
                    "SELECT id, sender_id, receiver_id, amount, signature, public_key "
                    "FROM transactions"
                ).fetchall()
                old_confirmed_ids = {row["id"] for row in old_tx_rows}
                old_tx_by_id = {row["id"]: _transaction_from_row(row) for row in old_tx_rows}
                mempool_ids = {
                    row["id"]
                    for row in conn.execute("SELECT id FROM mempool").fetchall()
                }
                unconfirmed_again = old_confirmed_ids - new_confirmed_ids

                conn.execute("DELETE FROM blocks")
                for block in blocks:
                    _insert_block(conn, block)

                if new_confirmed_ids:
                    placeholders = ",".join("?" for _ in new_confirmed_ids)
                    conn.execute(
                        f"DELETE FROM mempool WHERE id IN ({placeholders})",
                        list(new_confirmed_ids),
                    )

                next_seq_row = conn.execute("SELECT COALESCE(MAX(seq), -1) + 1 FROM mempool").fetchone()
                next_seq = next_seq_row[0]
                for tx_id in unconfirmed_again:
                    if tx_id in mempool_ids:
                        continue
                    tx = old_tx_by_id[tx_id]
                    tx_dto = transaction_to_dto(tx)
                    conn.execute(
                        "INSERT INTO mempool "
                        "(id, seq, sender_id, receiver_id, amount, signature, public_key) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            tx_dto.id,
                            next_seq,
                            tx_dto.sender_id,
                            tx_dto.receiver_id,
                            tx_dto.amount,
                            tx_dto.signature,
                            tx_dto.public_key,
                        ),
                    )
                    next_seq += 1

                conn.commit()

    def get_last_block(self) -> Block | None:
        with self._lock:
            with _connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT * FROM blocks ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if row is None:
                    return None
                return _load_block(conn, row)

    def get_height(self) -> int:
        with self._lock:
            with _connect(self._db_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM blocks").fetchone()
                return int(row[0])
