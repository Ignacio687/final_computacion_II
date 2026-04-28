"""Adaptador: verificación de firmas con la librería cryptography."""

from main.application.interfaces.verifier import IVerifier


class CryptographyVerifier(IVerifier):
    """Implementación de IVerifier. No requiere claves precargadas: la public_key
    viene en cada llamada a verify."""

    def verify(self, payload: bytes, signature: bytes, public_key: bytes) -> bool:
        raise NotImplementedError
