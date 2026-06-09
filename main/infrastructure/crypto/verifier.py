"""Adaptador: verificación de firmas con la librería cryptography."""

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization

from main.application.interfaces.verifier import IVerifier


class CryptographyVerifier(IVerifier):
    """Implementación de IVerifier con **Ed25519** (ver doc/protocolo.md §1.1). No requiere
    claves precargadas: `public_key` (bytes DER, SubjectPublicKeyInfo) viene en cada llamada.
    Carga la clave con `Ed25519PublicKey.from_public_bytes`/`load_der_public_key` y devuelve
    False si `verify` lanza `InvalidSignature`."""

    def verify(self, payload: bytes, signature: bytes, public_key: bytes) -> bool:
        try:
            key = serialization.load_der_public_key(public_key)
            key.verify(signature, payload)
            return True
        except InvalidSignature:
            return False
        except (ValueError, TypeError):
            return False
