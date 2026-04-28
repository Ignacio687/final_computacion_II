"""Interfaz: verificación de firmas."""

from abc import ABC, abstractmethod


class IVerifier(ABC):
    """Contrato para verificar firmas dadas (payload, signature, public_key)."""

    @abstractmethod
    def verify(self, payload: bytes, signature: bytes, public_key: bytes) -> bool:
        """Devuelve True si y solo si `signature` es una firma válida de `payload`
        producida por la clave privada correspondiente a `public_key`."""
        ...
