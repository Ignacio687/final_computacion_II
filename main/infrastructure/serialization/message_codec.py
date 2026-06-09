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

from main.application.interfaces.signer import ISigner
from main.application.interfaces.verifier import IVerifier
from main.domain.models.message import Message


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
        raise NotImplementedError

    def decode(self, raw: bytes, peer_public_key: bytes | None) -> Message:
        """Parsea el sobre (ver doc/protocolo.md §6.3): descifra el payload, verifica la
        firma y lo deserializa a la dataclass concreta según el `type` (mapeo estricto §6.4).

        Verificación de firma:
        - Para `HELLO`, `peer_public_key` puede ser None: se usa la `public_key` que viene
          dentro del payload descifrado (TOFU).
        - Para el resto, `peer_public_key` es la clave registrada del peer (obligatoria).

        Lanza una excepción si la firma es inválida o el payload no corresponde al type."""
        raise NotImplementedError
