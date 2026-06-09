"""Cliente HTTP de la billetera hacia un nodo HashCoin."""

import dataclasses
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import List

from main.domain.models.transaction import Transaction
from main.repository.dto.mappers import transaction_from_dto, transaction_to_dto
from main.repository.dto.transaction_dto import TransactionDTO


class WalletClient:
    """Cliente HTTP usado por la consola de la billetera y por el generador de tx de prueba.

    Endpoints consumidos del nodo:
        GET  /balance?address=<addr>
        GET  /transactions?address=<addr|optional>&limit=<n>
        GET  /status
        POST /tx   (cuerpo JSON con la TransactionDTO firmada)

    `node_url` es la URL base (http://host:port), sin slash final.
    """

    def __init__(
        self,
        node_url: str,
        fallback_node_urls: tuple[str, ...] | list[str] = (),
    ) -> None:
        self._node_urls = [node_url.rstrip("/")]
        self._node_urls.extend(url.rstrip("/") for url in fallback_node_urls)

    def get_balance(self, address: str) -> int:
        query = urllib.parse.urlencode({"address": address})
        data = self._request("GET", f"/balance?{query}")
        return int(data["balance"])

    def get_transactions(self, address: str | None, limit: int) -> List[Transaction]:
        params: dict[str, str] = {"limit": str(limit)}
        if address is not None:
            params["address"] = address
        query = urllib.parse.urlencode(params)
        payload = self._request("GET", f"/transactions?{query}")
        if not isinstance(payload, list):
            raise ValueError("La respuesta de /transactions debe ser una lista")
        return [
            transaction_from_dto(TransactionDTO(**item))
            for item in payload
        ]

    def get_status(self) -> dict:
        data = self._request("GET", "/status")
        if not isinstance(data, dict):
            raise ValueError("La respuesta de /status debe ser un objeto JSON")
        return data

    def submit_transaction(self, tx: Transaction) -> bool:
        """Devuelve True si el nodo aceptó la transacción (HTTP 200/201), False en caso contrario."""
        dto = transaction_to_dto(tx)
        body = json.dumps(dataclasses.asdict(dto)).encode("utf-8")
        try:
            response = self._request(
                "POST",
                "/tx",
                data=body,
                headers={"Content-Type": "application/json"},
            )
        except urllib.error.HTTPError:
            return False
        if not isinstance(response, dict):
            return False
        return bool(response.get("accepted"))

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> object:
        request_headers = dict(headers or {})
        last_error: Exception | None = None
        for base_url in self._node_urls:
            url = f"{base_url}{path}"
            req = urllib.request.Request(
                url, data=data, method=method, headers=request_headers
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    raw = resp.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                if method == "POST" and path == "/tx":
                    raise exc
                if exc.code >= 500:
                    last_error = exc
                    continue
                raw = exc.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
            except urllib.error.URLError as exc:
                last_error = exc
                continue
            else:
                if not raw:
                    return {}
                return json.loads(raw)
        if last_error is not None:
            raise last_error
        raise urllib.error.URLError("no hay nodos disponibles")
