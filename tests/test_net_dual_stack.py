import asyncio

import pytest

from main.infrastructure.net.dual_stack import open_tcp_connection, start_stream_server


@pytest.mark.asyncio
async def test_dual_stack_server_accepts_ipv4_loopback():
    connected = asyncio.Event()

    async def on_client(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        connected.set()
        writer.close()
        await writer.wait_closed()

    server = await start_stream_server(on_client, "auto", 0)
    try:
        port = server.sockets[0].getsockname()[1]
        reader, writer = await open_tcp_connection("127.0.0.1", port)
        await asyncio.wait_for(connected.wait(), timeout=2.0)
        writer.close()
        await writer.wait_closed()
        reader.feed_eof()
    finally:
        server.close()
        await server.wait_closed()
