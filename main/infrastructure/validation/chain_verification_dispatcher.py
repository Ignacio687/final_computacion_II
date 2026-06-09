"""Dispatcher de verificación pesada de cadenas: cola de tareas + workers en hilos."""

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
    def __init__(self, chain_verifier: IChainVerifier, workers: int = 1) -> None:
        self._chain_verifier = chain_verifier
        self._workers = workers
        self._task_queue: Optional[queue.Queue] = None
        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []

    def start(self) -> None:
        self._task_queue = queue.Queue()
        self._stop_event.clear()
        self._threads = []
        for _ in range(self._workers):
            thread = threading.Thread(target=self._worker_loop, daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop_event.set()
        if self._task_queue is not None:
            while True:
                try:
                    item = self._task_queue.get_nowait()
                except queue.Empty:
                    break
                if item is not _SENTINEL:
                    task: _VerificationTask = item
                    if not task.future.done():
                        task.loop.call_soon_threadsafe(task.future.cancel)
            for _ in range(self._workers):
                self._task_queue.put(_SENTINEL)
        for thread in self._threads:
            thread.join()
        self._threads.clear()
        self._task_queue = None

    async def verify(self, blocks: List[Block]) -> bool:
        if self._task_queue is None:
            raise RuntimeError("ChainVerificationDispatcher no está iniciado")

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        task = _VerificationTask(blocks=blocks, future=future, loop=loop)
        self._task_queue.put(task)
        try:
            return await future
        except asyncio.CancelledError:
            return False

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            item = self._task_queue.get()
            if item is _SENTINEL:
                break
            task: _VerificationTask = item
            if task.future.cancelled():
                continue
            try:
                result = self._chain_verifier.verify_chain(task.blocks)
            except Exception:
                result = False
            if not task.future.done():
                task.loop.call_soon_threadsafe(task.future.set_result, result)
