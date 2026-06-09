"""Interfaz: firma de datos."""

from abc import ABC, abstractmethod


class ISigner(ABC):
    """Contrato para firmar bytes con la clave privada del nodo o usuario.
    Algoritmo: Ed25519 (ver doc/protocolo.md §1.1)."""

    @abstractmethod
    def sign(self, payload: bytes) -> bytes:
        """Devuelve la firma Ed25519 (bytes crudos) del payload usando la clave privada
        cargada en el adaptador."""
        ...

    @abstractmethod
    def get_public_key(self) -> bytes:
        """Devuelve la clave pública correspondiente en bytes DER (SubjectPublicKeyInfo),
        para que los receptores verifiquen."""
        ...
