"""Dispatcher de verificación pesada de cadenas: cola de tareas + workers en hilos.

Cubre el requisito de cola de tareas distribuidas de la materia (queue.Queue + threading):
la verificación de una cadena completa (IChainVerifier) es CPU/IO-bound y no debe bloquear
el event loop. El flujo (ver doc/funcionalidades.md "Verificación de cadena"):

    1. PropagationService encola una tarea (la cadena a verificar) en una `queue.Queue`.
    2. N worker threads toman tareas y ejecutan `chain_verifier.verify_chain(blocks)`.
    3. El resultado se devuelve al event loop asyncio de forma thread-safe
       (loop.call_soon_threadsafe sobre un asyncio.Future / asyncio.Queue).

Mantenerlo mínimo: 1-2 workers alcanzan para una red local de 4-5 nodos.
"""

import asyncio
import queue
import threading
from dataclasses import dataclass
from typing import List, Optional

from main.application.interfaces.chain_verifier import IChainVerifier
from main.domain.models.block import Block

_SENTINEL = object()


@dataclass
class _VerificationTask:
    blocks: List[Block]
    future: asyncio.Future
    loop: asyncio.AbstractEventLoop


class ChainVerificationDispatcher:
    """Encola cadenas para verificar en worker threads y devuelve el resultado al loop."""

    def __init__(self, chain_verifier: IChainVerifier, workers: int = 1) -> None:
        self._chain_verifier = chain_verifier
        self._workers = workers
        self._task_queue: Optional[queue.Queue] = None
        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []

    def start(self) -> None:
        """Crea la `queue.Queue` y arranca los worker threads."""
        self._task_queue = queue.Queue()
        self._stop_event.clear()
        self._threads = []
        for _ in range(self._workers):
            thread = threading.Thread(target=self._worker_loop, daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        """Señaliza el fin a los workers y hace join."""
        self._stop_event.set()
        if self._task_queue is not None:
            for _ in range(self._workers):
                self._task_queue.put(_SENTINEL)
        for thread in self._threads:
            thread.join()
        self._threads.clear()
        self._task_queue = None

    async def verify(self, blocks: List[Block]) -> bool:
        """Encola la cadena y espera (sin bloquear el loop) el resultado del worker."""
        if self._task_queue is None:
            raise RuntimeError("ChainVerificationDispatcher no está iniciado")

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        task = _VerificationTask(blocks=blocks, future=future, loop=loop)
        self._task_queue.put(task)
        return await future

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            item = self._task_queue.get()
            if item is _SENTINEL:
                break
            task: _VerificationTask = item
            try:
                result = self._chain_verifier.verify_chain(task.blocks)
            except Exception:
                result = False
            task.loop.call_soon_threadsafe(task.future.set_result, result)
