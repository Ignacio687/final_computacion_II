"""Información de un peer (nodo) para conectividad."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeInfo:
    """Datos de conexión de un nodo peer.

    node_id es None hasta que se completa el handshake HELLO con el peer (doc/protocolo.md
    §6.5); a partir de ahí queda definido junto con la clave pública registrada del peer."""

    host: str
    port: int
    node_id: str | None = None
