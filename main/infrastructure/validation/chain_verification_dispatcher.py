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

from typing import List

from main.application.interfaces.chain_verifier import IChainVerifier
from main.domain.models.block import Block


class ChainVerificationDispatcher:
    """Encola cadenas para verificar en worker threads y devuelve el resultado al loop."""

    def __init__(self, chain_verifier: IChainVerifier, workers: int = 1) -> None:
        self._chain_verifier = chain_verifier
        self._workers = workers

    def start(self) -> None:
        """Crea la `queue.Queue` y arranca los worker threads."""
        raise NotImplementedError

    def stop(self) -> None:
        """Señaliza el fin a los workers y hace join."""
        raise NotImplementedError

    async def verify(self, blocks: List[Block]) -> bool:
        """Encola la cadena y espera (sin bloquear el loop) el resultado del worker."""
        raise NotImplementedError
