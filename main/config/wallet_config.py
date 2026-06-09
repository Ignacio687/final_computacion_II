"""Configuración de la billetera (parseada con argparse en run.py)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WalletConfig:
    """Configuración completa de la billetera. Todos los campos son obligatorios."""

    node_url: str                          # URL del nodo (http://host:port)
    fallback_node_urls: tuple[str, ...]    # URLs alternativas si la principal no responde
    keys_dir: str                          # directorio donde guardar/leer pares de claves PEM
    generator_mode: bool                   # si True, generar transacciones de prueba
    generator_users: int                   # cantidad de usuarios aleatorios a crear en modo generador
    generator_interval_seconds: float      # intervalo entre transacciones generadas
    genesis_seed: str                      # semilla del génesis (deriva las cuentas pre-fondeadas a gastar)
