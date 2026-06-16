"""Codec del sobre TCP: (de)serialización, cifrado del payload y firma del nodo.

Implementa el formato del sobre definido en doc/protocolo.md §6.2-§6.4 y §9:

    sobre = {
        "sender_node_id": str,
        "type":           str (MessageType),
        "payload_cipher": base64(AES-GCM(clave_precompartida, json_canonico(payload))),
        "signature":      base64(firma_nodo(json_canonico({sender_node_id, type, payload_cipher}))),
    }

El framing (4 bytes big-endian + cuerpo) lo aplican el sender/receiver, no este codec.
"""

import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from main.application.interfaces.signer import ISigner
from main.application.interfaces.verifier import IVerifier
from main.domain.models.message import Message, MessageType
from main.domain.models.payloads import (
    ChainResponsePayload,
    GetChainPayload,
    GetMempoolPayload,
    HelloPayload,
    MempoolResponsePayload,
    MessagePayload,
    NewBlockPayload,
    NewTxPayload,
)
from main.infrastructure.serialization.canonical import (
    b64_to_bytes,
    bytes_to_b64,
    json_canonical,
)
from main.repository.dto.block_dto import BlockDTO
from main.repository.dto.transaction_dto import TransactionDTO


class MessageCodec:
    """Construye y parsea sobres TCP.

    - `signer`: firma del nodo local (al construir sobres salientes).
    - `verifier`: verificación de firma de sobres entrantes contra la clave pública del
      peer (obtenida en el handshake).
    - `shared_key`: clave simétrica precompartida (32 bytes) para AES-GCM del payload.
    """

    def __init__(self, signer: ISigner, verifier: IVerifier, shared_key: bytes) -> None:
        self._signer = signer
        self._verifier = verifier
        self._shared_key = shared_key

    def encode(self, message: Message, sender_node_id: str) -> bytes:
        """Serializa el payload según `message.type`, lo cifra, firma el sobre y devuelve
        los bytes del sobre JSON (sin el prefijo de longitud)."""
        payload_dict = self._payload_to_dict(message.type, message.payload)
        payload_cipher = self._encrypt(json_canonical(payload_dict))
        envelope_firmable = {
            "sender_node_id": sender_node_id,
            "type": message.type.value,
            "payload_cipher": payload_cipher,
        }
        signature = self._signer.sign(json_canonical(envelope_firmable))
        envelope = {
            **envelope_firmable,
            "signature": bytes_to_b64(signature),
        }
        return json.dumps(envelope).encode("utf-8")

    def decode(
        self,
        raw: bytes,
        peer_public_key: bytes | None,
        *,
        expected_sender_node_id: str | None = None,
    ) -> Message:
        """Parsea el sobre (ver doc/protocolo.md §6.3): descifra el payload, verifica la
        firma y lo deserializa a la dataclass concreta según el `type` (mapeo estricto §6.4).

        Verificación de firma:
        - Para `HELLO`, `peer_public_key` puede ser None: se usa la `public_key` que viene
          dentro del payload descifrado (TOFU).
        - Para el resto, `peer_public_key` es la clave registrada del peer (obligatoria).

        Si `expected_sender_node_id` está definido (post-handshake), el sobre debe coincidir
        con el `node_id` registrado del peer (§6.3).

        Lanza una excepción si la firma es inválida o el payload no corresponde al type."""
        envelope = json.loads(raw.decode("utf-8"))
        sender_node_id = envelope["sender_node_id"]
        if (
            expected_sender_node_id is not None
            and sender_node_id != expected_sender_node_id
        ):
            raise ValueError(
                "sender_node_id del sobre no coincide con el peer registrado"
            )
        msg_type = MessageType(envelope["type"])
        payload_cipher = envelope["payload_cipher"]
        signature = b64_to_bytes(envelope["signature"])
        firmable = json_canonical(
            {
                "sender_node_id": sender_node_id,
                "type": msg_type.value,
                "payload_cipher": payload_cipher,
            }
        )
        payload_bytes = self._decrypt(payload_cipher)
        payload_dict = json.loads(payload_bytes.decode("utf-8"))
        verify_key = self._resolve_verify_key(
            msg_type, payload_dict, peer_public_key
        )
        if not self._verifier.verify(firmable, signature, verify_key):
            raise ValueError("Firma inválida en el sobre TCP")
        payload = self._dict_to_payload(msg_type, payload_dict)
        return Message(type=msg_type, payload=payload)

    def _encrypt(self, plaintext: bytes) -> str:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._shared_key).encrypt(nonce, plaintext, None)
        return bytes_to_b64(nonce + ciphertext)

    def _decrypt(self, payload_cipher: str) -> bytes:
        data = b64_to_bytes(payload_cipher)
        nonce = data[:12]
        ciphertext = data[12:]
        return AESGCM(self._shared_key).decrypt(nonce, ciphertext, None)

    def _resolve_verify_key(
        self,
        msg_type: MessageType,
        payload_dict: dict[str, Any],
        peer_public_key: bytes | None,
    ) -> bytes:
        if msg_type == MessageType.HELLO:
            if peer_public_key is not None:
                return peer_public_key
            return b64_to_bytes(self._require_str(payload_dict, "public_key"))
        if peer_public_key is None:
            raise ValueError("Se requiere la clave pública del peer para mensajes no-HELLO")
        return peer_public_key

    def _payload_to_dict(
        self, msg_type: MessageType, payload: MessagePayload
    ) -> dict[str, Any]:
        if msg_type == MessageType.HELLO:
            if not isinstance(payload, HelloPayload):
                raise TypeError("Payload incompatible con HELLO")
            return {
                "node_id": payload.node_id,
                "public_key": payload.public_key,
                "listen_port": payload.listen_port,
            }
        if msg_type == MessageType.NEW_TX:
            if not isinstance(payload, NewTxPayload):
                raise TypeError("Payload incompatible con NEW_TX")
            return {"transaction": self._transaction_dto_to_dict(payload.transaction)}
        if msg_type == MessageType.NEW_BLOCK:
            if not isinstance(payload, NewBlockPayload):
                raise TypeError("Payload incompatible con NEW_BLOCK")
            return {"block": self._block_dto_to_dict(payload.block)}
        if msg_type == MessageType.GET_CHAIN:
            if not isinstance(payload, GetChainPayload):
                raise TypeError("Payload incompatible con GET_CHAIN")
            return {"since_height": payload.since_height}
        if msg_type == MessageType.CHAIN_RESPONSE:
            if not isinstance(payload, ChainResponsePayload):
                raise TypeError("Payload incompatible con CHAIN_RESPONSE")
            return {
                "blocks": [
                    self._block_dto_to_dict(block) for block in payload.blocks
                ]
            }
        if msg_type == MessageType.GET_MEMPOOL:
            if not isinstance(payload, GetMempoolPayload):
                raise TypeError("Payload incompatible con GET_MEMPOOL")
            return {}
        if msg_type == MessageType.MEMPOOL_RESPONSE:
            if not isinstance(payload, MempoolResponsePayload):
                raise TypeError("Payload incompatible con MEMPOOL_RESPONSE")
            return {
                "transactions": [
                    self._transaction_dto_to_dict(tx)
                    for tx in payload.transactions
                ]
            }
        raise ValueError(f"Tipo de mensaje no soportado: {msg_type}")

    def _dict_to_payload(
        self, msg_type: MessageType, payload_dict: dict[str, Any]
    ) -> MessagePayload:
        if msg_type == MessageType.HELLO:
            return HelloPayload(
                node_id=self._require_str(payload_dict, "node_id"),
                public_key=self._require_str(payload_dict, "public_key"),
                listen_port=self._require_int(payload_dict, "listen_port"),
            )
        if msg_type == MessageType.NEW_TX:
            transaction = payload_dict.get("transaction")
            if not isinstance(transaction, dict):
                raise ValueError("Payload NEW_TX inválido: falta transaction")
            return NewTxPayload(transaction=self._dict_to_transaction_dto(transaction))
        if msg_type == MessageType.NEW_BLOCK:
            block = payload_dict.get("block")
            if not isinstance(block, dict):
                raise ValueError("Payload NEW_BLOCK inválido: falta block")
            return NewBlockPayload(block=self._dict_to_block_dto(block))
        if msg_type == MessageType.GET_CHAIN:
            return GetChainPayload(
                since_height=self._require_int(payload_dict, "since_height")
            )
        if msg_type == MessageType.CHAIN_RESPONSE:
            blocks = payload_dict.get("blocks")
            if not isinstance(blocks, list):
                raise ValueError("Payload CHAIN_RESPONSE inválido: falta blocks")
            return ChainResponsePayload(
                blocks=[self._dict_to_block_dto(block) for block in blocks]
            )
        if msg_type == MessageType.GET_MEMPOOL:
            if payload_dict:
                raise ValueError("Payload GET_MEMPOOL debe estar vacío")
            return GetMempoolPayload()
        if msg_type == MessageType.MEMPOOL_RESPONSE:
            transactions = payload_dict.get("transactions")
            if not isinstance(transactions, list):
                raise ValueError("Payload MEMPOOL_RESPONSE inválido: falta transactions")
            return MempoolResponsePayload(
                transactions=[
                    self._dict_to_transaction_dto(tx) for tx in transactions
                ]
            )
        raise ValueError(f"Tipo de mensaje no soportado: {msg_type}")

    def _transaction_dto_to_dict(self, tx: TransactionDTO) -> dict[str, Any]:
        return {
            "id": tx.id,
            "sender_id": tx.sender_id,
            "receiver_id": tx.receiver_id,
            "amount": tx.amount,
            "signature": tx.signature,
            "public_key": tx.public_key,
        }

    def _dict_to_transaction_dto(self, data: dict[str, Any]) -> TransactionDTO:
        return TransactionDTO(
            id=self._require_str(data, "id"),
            sender_id=self._require_str(data, "sender_id"),
            receiver_id=self._require_str(data, "receiver_id"),
            amount=self._require_int(data, "amount"),
            signature=self._require_str(data, "signature"),
            public_key=self._require_str(data, "public_key"),
        )

    def _block_dto_to_dict(self, block: BlockDTO) -> dict[str, Any]:
        return {
            "id": block.id,
            "last_hash": block.last_hash,
            "hash": block.hash,
            "timestamp": block.timestamp,
            "target": block.target,
            "nonce": block.nonce,
            "transactions": [
                self._transaction_dto_to_dict(tx) for tx in block.transactions
            ],
        }

    def _dict_to_block_dto(self, data: dict[str, Any]) -> BlockDTO:
        transactions = data.get("transactions")
        if not isinstance(transactions, list):
            raise ValueError("Bloque inválido: falta transactions")
        return BlockDTO(
            id=self._require_int(data, "id"),
            last_hash=self._require_str(data, "last_hash"),
            hash=self._require_str(data, "hash"),
            timestamp=self._require_number(data, "timestamp"),
            target=self._require_int(data, "target"),
            nonce=self._require_int(data, "nonce"),
            transactions=[
                self._dict_to_transaction_dto(tx) for tx in transactions
            ],
        )

    def _require_str(self, data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str):
            raise ValueError(f"Campo inválido: {key}")
        return value

    def _require_int(self, data: dict[str, Any], key: str) -> int:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Campo inválido: {key}")
        return value

    def _require_number(self, data: dict[str, Any], key: str) -> float:
        value = data.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"Campo inválido: {key}")
        return float(value)
