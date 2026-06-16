"""Adaptador: firma de datos con la librería cryptography."""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.application.interfaces.signer import ISigner


class CryptographySigner(ISigner):
    """Implementación de ISigner que carga el par de claves del nodo desde archivos PEM.

        PEM (Privacy-Enhanced Mail, RFC 7468) es el formato estándar de texto para
        almacenar claves criptográficas: el contenido va entre delimitadores
        `-----BEGIN PRIVATE KEY-----` / `-----END PRIVATE KEY-----` (o PUBLIC KEY).

    Por qué el NODO tiene par de claves propio (independiente de los usuarios):
        Los usuarios firman sus TRANSACCIONES con sus propias claves (administradas por
        la billetera). El nodo, en cambio, firma cada MENSAJE TCP que envía a otros peers
        (NEW_TX, NEW_BLOCK, GET_CHAIN, CHAIN_RESPONSE, etc.) con la clave privada del
        nodo. Esto sirve para:
            - Autenticación: el peer verifica con la clave pública del nodo emisor que
              el mensaje provino de un nodo conocido y no de un atacante.
            - Integridad: detecta cualquier modificación del mensaje en tránsito.
        El cifrado del canal (confidencialidad) se resuelve por separado con una clave
        simétrica precompartida (AES-GCM, ver doc/protocolo.md §9).

    `private_key_path` y `public_key_path` apuntan a archivos PEM del nodo. Son distintos
    de las claves de los usuarios, que viven en `WalletAccount` dentro de la billetera.

    Algoritmo: **Ed25519** (ver doc/protocolo.md §1.1). `sign` devuelve los bytes crudos de
    `Ed25519PrivateKey.sign(payload)`; `get_public_key` devuelve la clave pública en bytes
    **DER** (SubjectPublicKeyInfo).
    """

    def __init__(self, private_key_path: str, public_key_path: str) -> None:
        self._private_key_path = private_key_path
        self._public_key_path = public_key_path
        self._private_key = self._load_private_key()
        self._public_key_der = self._load_public_key_der()

    def _load_private_key(self) -> Ed25519PrivateKey:
        with open(self._private_key_path, "rb") as key_file:
            key = serialization.load_pem_private_key(key_file.read(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("Se esperaba una clave privada Ed25519")
        return key

    def _load_public_key_der(self) -> bytes:
        with open(self._public_key_path, "rb") as key_file:
            public_key = serialization.load_pem_public_key(key_file.read())
        return public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def sign(self, payload: bytes) -> bytes:
        return self._private_key.sign(payload)

    def get_public_key(self) -> bytes:
        return self._public_key_der
