import asyncio
import logging
import socket

import pytest

from main.infrastructure.net.dual_stack import (
    listen_label,
    listen_label_from_sockets,
    open_tcp_connection,
    start_stream_server,
)


@pytest.mark.asyncio
async def test_auto_opens_native_ipv4_and_ipv6_sockets():
    async def on_client(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.close()
        await writer.wait_closed()

    bundle = await start_stream_server(on_client, "auto", 0)
    try:
        families = {s.family for s in bundle.sockets}
        assert socket.AF_INET in families
        assert socket.AF_INET6 in families

        v6_socks = [s for s in bundle.sockets if s.family == socket.AF_INET6]
        assert v6_socks
        for sock in v6_socks:
            assert sock.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY) == 1

        ports = {s.getsockname()[1] for s in bundle.sockets}
        assert len(ports) == 1
    finally:
        bundle.close()
        await bundle.wait_closed()


@pytest.mark.asyncio
async def test_auto_accepts_ipv4_and_ipv6_without_mapped_peername():
    accepted: list[str] = []
    events = {
        "v4": asyncio.Event(),
        "v6": asyncio.Event(),
    }

    async def on_client(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")[0]
        accepted.append(peer)
        if ":" in peer and not peer.startswith("::ffff:"):
            events["v6"].set()
        else:
            events["v4"].set()
        writer.close()
        await writer.wait_closed()

    bundle = await start_stream_server(on_client, "auto", 0)
    try:
        port = bundle.sockets[0].getsockname()[1]

        r4, w4 = await open_tcp_connection("127.0.0.1", port)
        await asyncio.wait_for(events["v4"].wait(), timeout=2.0)
        w4.close()
        await w4.wait_closed()
        r4.feed_eof()

        r6, w6 = await open_tcp_connection("::1", port)
        await asyncio.wait_for(events["v6"].wait(), timeout=2.0)
        w6.close()
        await w6.wait_closed()
        r6.feed_eof()

        ipv4_peers = [p for p in accepted if ":" not in p]
        ipv6_peers = [p for p in accepted if ":" in p]
        assert ipv4_peers, f"expected IPv4 peername, got {accepted!r}"
        assert ipv6_peers, f"expected IPv6 peername, got {accepted!r}"
        assert all(not p.startswith("::ffff:") for p in accepted)
    finally:
        bundle.close()
        await bundle.wait_closed()


@pytest.mark.asyncio
async def test_auto_degrades_to_ipv4_with_warning(monkeypatch, caplog):
    import main.infrastructure.net.dual_stack as dual_stack_mod

    real_make = dual_stack_mod._make_listening_socket

    def make_failing_v6(family, address, *, v6only=None):
        if family == socket.AF_INET6:
            raise OSError("simulated IPv6 bind failure")
        return real_make(family, address, v6only=v6only)

    monkeypatch.setattr(dual_stack_mod, "_make_listening_socket", make_failing_v6)

    async def on_client(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.close()
        await writer.wait_closed()

    with caplog.at_level(logging.WARNING, logger="net"):
        bundle = await start_stream_server(on_client, "auto", 0)
    try:
        families = {s.family for s in bundle.sockets}
        assert families == {socket.AF_INET}
        assert any("IPv6" in r.message for r in caplog.records)
        label = listen_label_from_sockets(bundle.sockets, bundle.sockets[0].getsockname()[1])
        assert "0.0.0.0" in label
        assert "[::]" not in label
    finally:
        bundle.close()
        await bundle.wait_closed()


@pytest.mark.asyncio
async def test_explicit_ipv4_bind_single_family():
    async def on_client(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.close()
        await writer.wait_closed()

    bundle = await start_stream_server(on_client, "127.0.0.1", 0)
    try:
        assert all(s.family == socket.AF_INET for s in bundle.sockets)
        port = bundle.sockets[0].getsockname()[1]
        reader, writer = await open_tcp_connection("127.0.0.1", port)
        writer.close()
        await writer.wait_closed()
        reader.feed_eof()
    finally:
        bundle.close()
        await bundle.wait_closed()


@pytest.mark.asyncio
async def test_explicit_ipv6_bind_single_family():
    async def on_client(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.close()
        await writer.wait_closed()

    bundle = await start_stream_server(on_client, "::1", 0)
    try:
        assert all(s.family == socket.AF_INET6 for s in bundle.sockets)
        port = bundle.sockets[0].getsockname()[1]
        reader, writer = await open_tcp_connection("::1", port)
        writer.close()
        await writer.wait_closed()
        reader.feed_eof()
    finally:
        bundle.close()
        await bundle.wait_closed()


def test_listen_label_auto_says_native_not_dual_stack():
    label = listen_label("auto", 8001)
    assert "nativo" in label
    assert "dual-stack" not in label
    assert "0.0.0.0" in label
    assert "[::]" in label
