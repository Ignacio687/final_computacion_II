"""Adaptador HTTP: servidor del nodo (GET /balance, GET /transactions, GET /status, POST /tx)."""

import asyncio
import json
import urllib.parse
from typing import Optional

from main.controller.http_handlers import HTTPHandlers
from main.infrastructure.http.limits import (
    MAX_HEADER_BYTES,
    MAX_POST_BODY_BYTES,
    MAX_TRANSACTIONS_LIMIT,
)


class HTTPServer:
    """Servidor HTTP del nodo (doc/protocolo.md §10.1)."""

    def __init__(self, bind_host: str, port: int, handlers: HTTPHandlers) -> None:
        self._bind_host = bind_host
        self._port = port
        self._handlers = handlers
        self._server: Optional[asyncio.Server] = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            self._bind_host,
            self._port,
        )

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            status_code, body = await self._process_request(reader)
            response_body = json.dumps(body, separators=(",", ":")).encode("utf-8")
            reason_by_code = {
                200: "OK",
                400: "Bad Request",
                404: "Not Found",
                413: "Payload Too Large",
            }
            reason = reason_by_code.get(status_code, "Error")
            headers = (
                f"HTTP/1.1 {status_code} {reason}\r\n"
                f"Content-Type: application/json\r\n"
                f"Connection: close\r\n"
                f"Content-Length: {len(response_body)}\r\n"
                f"\r\n"
            )
            writer.write(headers.encode("ascii") + response_body)
            await writer.drain()
        except Exception:
            error_body = json.dumps({"error": "bad request"}).encode("utf-8")
            writer.write(
                (
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Content-Type: application/json\r\n"
                    "Connection: close\r\n"
                    f"Content-Length: {len(error_body)}\r\n"
                    "\r\n"
                ).encode("ascii")
                + error_body
            )
            await writer.drain()
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _read_headers(self, reader: asyncio.StreamReader) -> bytes:
        buffer = b""
        while True:
            if len(buffer) >= MAX_HEADER_BYTES:
                raise ValueError("cabeceras HTTP exceden MAX_HEADER_BYTES")
            chunk = await reader.read(1)
            if not chunk:
                raise asyncio.IncompleteReadError(buffer, 1)
            buffer += chunk
            if buffer.endswith(b"\r\n\r\n"):
                return buffer

    async def _process_request(
        self, reader: asyncio.StreamReader
    ) -> tuple[int, object]:
        try:
            header_data = await self._read_headers(reader)
        except ValueError:
            return 400, {"error": "bad request"}
        header_text = header_data.decode("utf-8", errors="replace")
        lines = header_text.split("\r\n")
        if not lines:
            return 400, {"error": "bad request"}

        request_line = lines[0].split()
        if len(request_line) < 2:
            return 400, {"error": "bad request"}
        method = request_line[0].upper()
        target = request_line[1]

        headers: dict[str, str] = {}
        for line in lines[1:]:
            if not line or ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()

        path, _, query_string = target.partition("?")
        query = urllib.parse.parse_qs(query_string, keep_blank_values=True)

        body = b""
        if method == "POST":
            try:
                content_length = int(headers.get("content-length", "0"))
            except ValueError:
                return 400, {"error": "bad request"}
            if content_length < 0:
                return 400, {"error": "bad request"}
            if content_length > MAX_POST_BODY_BYTES:
                return 413, {"error": "payload too large"}
            if content_length > 0:
                body = await reader.readexactly(content_length)

        if method == "GET" and path == "/balance":
            address_list = query.get("address")
            if not address_list or not address_list[0]:
                return 400, {"error": "address required"}
            return 200, await self._handlers.handle_get_balance(address_list[0])

        if method == "GET" and path == "/transactions":
            address_list = query.get("address")
            address = address_list[0] if address_list else None
            limit = 50
            if "limit" in query and query["limit"]:
                try:
                    limit = int(query["limit"][0])
                except ValueError:
                    return 400, {"error": "invalid limit"}
                if limit < 1:
                    return 400, {"error": "invalid limit"}
                limit = min(limit, MAX_TRANSACTIONS_LIMIT)
            return 200, await self._handlers.handle_get_transactions(address, limit)

        if method == "GET" and path == "/status":
            return 200, await self._handlers.handle_get_status()

        if method == "POST" and path == "/tx":
            return await self._handlers.handle_post_tx(body)

        return 404, {"error": "not found"}
