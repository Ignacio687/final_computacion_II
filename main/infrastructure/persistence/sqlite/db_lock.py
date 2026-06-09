"""Lock compartido por db_path entre repositorios SQLite del mismo nodo."""

import threading

_locks: dict[str, threading.Lock] = {}


def get_db_lock(db_path: str) -> threading.Lock:
    if db_path not in _locks:
        _locks[db_path] = threading.Lock()
    return _locks[db_path]
