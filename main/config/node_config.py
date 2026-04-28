"""Configuración del nodo (parseada con argparse en run.py)."""

from dataclasses import dataclass
from typing import List

from main.domain.models.node_info import NodeInfo


@dataclass(frozen=True)
class NodeConfig:
    """Configuración completa de un nodo. Todos los campos son obligatorios."""

    # Identidad y red
    node_id: str                          # identificador único del nodo en la red
    bind_host: str                        # host donde escuchan los servidores TCP y HTTP
    tcp_port: int                         # puerto del protocolo entre nodos
    http_port: int                        # puerto del servidor HTTP (billetera/CLI)
    peers: List[NodeInfo]                 # peers iniciales (lista estática)

    # Persistencia
    db_path: str                          # ruta del archivo SQLite del nodo

    # Minado / PoW
    difficulty: int                       # cantidad de ceros hex iniciales requeridos en el hash
    pow_workers: int                      # procesos del ProcessPoolExecutor para PoW
    min_transactions_per_block: int       # mínimo de tx no-coinbase para minar un bloque
    block_interval_seconds: float         # tiempo máximo entre intentos de minado
    mining_reward: int                    # unidades de recompensa por bloque minado
    mining_address: str                   # dirección que recibe la recompensa

    # Claves del nodo
    private_key_path: str                 # archivo PEM con la clave privada del nodo
    public_key_path: str                  # archivo PEM con la clave pública del nodo

    # Conectividad TCP entre nodos
    ping_interval_seconds: float          # frecuencia con la que se envía PING a cada peer
    pong_timeout_seconds: float           # tiempo sin recibir PONG para considerar caída
    reconnect_initial_seconds: float      # backoff inicial al reconectar
    reconnect_max_seconds: float          # backoff máximo al reconectar

    # Génesis
    genesis_seed: str                     # semilla que define el bloque génesis (idéntica en toda la red)
