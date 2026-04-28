"""Interfaz: firma de datos."""

from abc import ABC, abstractmethod


class ISigner(ABC):
    """Contrato para firmar bytes con la clave privada del nodo o usuario."""

    @abstractmethod
    def sign(self, payload: bytes) -> bytes:
        """Devuelve la firma del payload usando la clave privada cargada en el adaptador."""
        ...

    @abstractmethod
    def get_public_key(self) -> bytes:
        """Devuelve la clave pública correspondiente (para que receptores verifiquen sin
        otro canal)."""
        ...
