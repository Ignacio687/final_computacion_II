"""Servidores y clientes TCP/HTTP con soporte dual-stack IPv4/IPv6."""

from __future__ import annotations

import asyncio
import socket
from typing import Any, Callable, Coroutine

from main.infrastructure.net.endpoints import format_host_port, resolve_bind_host, strip_host_brackets

ClientConnectedCb = Callable[
    [asyncio.StreamReader, asyncio.StreamWriter],
    Coroutine[Any, Any, None],
]


async def start_stream_server(
    client_connected_cb: ClientConnectedCb,
    bind_host: str,
    port: int,
) -> asyncio.Server:
    """Levanta un servidor asyncio; ``bind_host=auto`` usa dual-stack si el SO lo permite."""
    resolved = resolve_bind_host(bind_host)
    if resolved is None:
        return await _start_dual_stack_server(client_connected_cb, port)
    return await asyncio.start_server(client_connected_cb, host=resolved, port=port)


async def _start_dual_stack_server(
    client_connected_cb: ClientConnectedCb,
    port: int,
) -> asyncio.Server:
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(False)
        sock.bind(("::", port))
        sock.listen()
        return await asyncio.start_server(client_connected_cb, sock=sock)
    except OSError:
        return await asyncio.start_server(
            client_connected_cb, host="0.0.0.0", port=port
        )


async def open_tcp_connection(host: str, port: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Conexión saliente; resuelve hostname/IPv4/IPv6 vía ``getaddrinfo``."""
    return await asyncio.open_connection(strip_host_brackets(host), port)


def listen_label(bind_host: str, port: int) -> str:
    resolved = resolve_bind_host(bind_host)
    if resolved is None:
        return f"[::|0.0.0.0]:{port} (dual-stack)"
    return format_host_port(resolved, port)
