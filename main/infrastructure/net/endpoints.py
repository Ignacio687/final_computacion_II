"""Parsing y normalización de direcciones de red (IPv4/IPv6/hostnames)."""

from __future__ import annotations

import ipaddress

from main.domain.models.node_info import NodeInfo


def strip_host_brackets(host: str) -> str:
    host = host.strip()
    if host.startswith("[") and host.endswith("]"):
        return host[1:-1]
    return host


def parse_host_port(endpoint: str) -> tuple[str, int]:
    """Parsea ``host:port`` o ``[ipv6]:port``.

    Para literales IPv6 con ``:`` usar corchetes: ``[::1]:8001``.
    """
    endpoint = endpoint.strip()
    if not endpoint:
        raise ValueError("endpoint vacío")
    if endpoint.startswith("["):
        close = endpoint.index("]")
        host = endpoint[1:close]
        rest = endpoint[close + 1 :]
        if not rest.startswith(":"):
            raise ValueError(f"formato inválido: {endpoint!r}")
        port = int(rest[1:])
        return host, port
    if ":" not in endpoint:
        raise ValueError(f"se esperaba host:port, recibido: {endpoint!r}")
    host, port_str = endpoint.rsplit(":", 1)
    return host.strip(), int(port_str)


def parse_peers_string(peers: str) -> list[NodeInfo]:
    if not peers or not peers.strip():
        return []
    result: list[NodeInfo] = []
    for part in peers.split(","):
        part = part.strip()
        if not part:
            continue
        host, port = parse_host_port(part)
        result.append(NodeInfo(host=host, port=port))
    return result


def normalize_host(host: str) -> str:
    """Normaliza IP para comparación; hostnames en minúsculas."""
    host = strip_host_brackets(host)
    try:
        ip = ipaddress.ip_address(host)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            return str(ip.ipv4_mapped)
        return str(ip)
    except ValueError:
        return host.lower()


def hosts_match(configured: str, observed: str) -> bool:
    return normalize_host(configured) == normalize_host(observed)


def format_host_port(host: str, port: int) -> str:
    host = strip_host_brackets(host)
    try:
        ip = ipaddress.ip_address(host)
        if isinstance(ip, ipaddress.IPv6Address):
            return f"[{ip}]:{port}"
    except ValueError:
        pass
    return f"{host}:{port}"


def resolve_bind_host(bind_host: str) -> str | None:
    """``None`` = dual-stack automático; string = bind explícito."""
    value = bind_host.strip().lower()
    if value in {"", "auto", "*", "all"}:
        return None
    return strip_host_brackets(bind_host)
