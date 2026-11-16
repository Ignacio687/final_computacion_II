"""Servidores y clientes TCP/HTTP con escucha IPv4/IPv6 nativa (sockets dedicados)."""

from __future__ import annotations

import asyncio
import socket
from typing import Any, Callable, Coroutine, Sequence

from main.infrastructure.logging.node_logger import get_logger
from main.infrastructure.net.endpoints import format_host_port, resolve_bind_host, strip_host_brackets

ClientConnectedCb = Callable[
    [asyncio.StreamReader, asyncio.StreamWriter],
    Coroutine[Any, Any, None],
]

logger = get_logger("net")


class StreamServerBundle:
    """Agrupa uno o más ``asyncio.Server`` (p.ej. IPv4 + IPv6 en ``auto``)."""

    def __init__(self, servers: Sequence[asyncio.Server]) -> None:
        if not servers:
            raise ValueError("StreamServerBundle requiere al menos un server")
        self._servers = list(servers)

    @property
    def sockets(self) -> list[socket.socket]:
        result: list[socket.socket] = []
        for server in self._servers:
            if server.sockets:
                result.extend(server.sockets)
        return result

    def close(self) -> None:
        for server in self._servers:
            server.close()

    async def wait_closed(self) -> None:
        for server in self._servers:
            await server.wait_closed()


async def start_stream_server(
    client_connected_cb: ClientConnectedCb,
    bind_host: str,
    port: int,
) -> StreamServerBundle:
    """Levanta servidor(es); ``bind_host=auto`` usa sockets IPv4+IPv6 nativos dedicados."""
    resolved = resolve_bind_host(bind_host)
    if resolved is None:
        return await _start_native_auto_servers(client_connected_cb, port)
    server = await asyncio.start_server(client_connected_cb, host=resolved, port=port)
    return StreamServerBundle([server])


def _make_listening_socket(
    family: int,
    address: tuple[Any, ...],
    *,
    v6only: bool | None = None,
) -> socket.socket:
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        if family == socket.AF_INET6 and v6only is not None:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1 if v6only else 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(False)
        sock.bind(address)
        sock.listen()
    except OSError:
        sock.close()
        raise
    return sock


async def _start_native_auto_servers(
    client_connected_cb: ClientConnectedCb,
    port: int,
) -> StreamServerBundle:
    """Binds dedicados AF_INET + AF_INET6(V6ONLY=1); degrada a IPv4-only si falla IPv6."""
    v4_sock = _make_listening_socket(socket.AF_INET, ("0.0.0.0", port))
    effective_port = v4_sock.getsockname()[1]

    servers: list[asyncio.Server] = [
        await asyncio.start_server(client_connected_cb, sock=v4_sock)
    ]

    try:
        v6_sock = _make_listening_socket(
            socket.AF_INET6,
            ("::", effective_port),
            v6only=True,
        )
    except OSError:
        logger.warning(
            "net: IPv6 no disponible al bindear :::%s; se continúa solo con IPv4 (0.0.0.0)",
            effective_port,
        )
        return StreamServerBundle(servers)

    servers.append(await asyncio.start_server(client_connected_cb, sock=v6_sock))
    return StreamServerBundle(servers)


async def open_tcp_connection(host: str, port: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Conexión saliente; resuelve hostname/IPv4/IPv6 vía ``getaddrinfo``."""
    return await asyncio.open_connection(strip_host_brackets(host), port)


def listen_label(bind_host: str, port: int) -> str:
    """Label pretendido según ``bind_host`` (sin inspeccionar sockets reales)."""
    resolved = resolve_bind_host(bind_host)
    if resolved is None:
        return f"0.0.0.0+[::]:{port} (nativo)"
    return format_host_port(resolved, port)


def listen_label_from_sockets(sockets: Sequence[socket.socket], port: int) -> str:
    """Label según familias realmente abiertas (útil tras degradación IPv6)."""
    has_v4 = any(s.family == socket.AF_INET for s in sockets)
    has_v6 = any(s.family == socket.AF_INET6 for s in sockets)
    if has_v4 and has_v6:
        return f"0.0.0.0+[::]:{port} (nativo)"
    if has_v4:
        return f"0.0.0.0:{port}"
    if has_v6:
        return f"[::]:{port}"
    return f"?:{port}"
