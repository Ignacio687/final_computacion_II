"""Información de un peer (nodo) para conectividad."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeInfo:
    """Datos de conexión de un nodo peer.

    node_id es None hasta que se completa el primer intercambio de mensajes con el peer
    (queda definido cuando el peer envía su primer mensaje firmado y se identifica)."""

    host: str
    port: int
    node_id: str | None = None
