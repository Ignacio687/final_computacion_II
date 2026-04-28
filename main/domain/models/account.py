"""Cuenta pública (visible en la blockchain): identificador y clave pública."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    """Cuenta pública. Es lo que conoce el nodo y lo que viaja en mensajes/transacciones.
    No contiene clave privada ni balance."""

    id: str
    public_key: bytes
