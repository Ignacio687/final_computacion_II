"""Interfaz: verificación de firmas."""

from abc import ABC, abstractmethod


class IVerifier(ABC):
    """Contrato para verificar firmas dadas (payload, signature, public_key).
    Algoritmo: Ed25519; `public_key` en bytes DER (ver doc/protocolo.md §1.1)."""

    @abstractmethod
    def verify(self, payload: bytes, signature: bytes, public_key: bytes) -> bool:
        """Devuelve True si y solo si `signature` es una firma Ed25519 válida de `payload`
        producida por la clave privada correspondiente a `public_key` (DER). No lanza:
        ante firma inválida devuelve False."""
        ...
