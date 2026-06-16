"""Identidad criptográfica local de la billetera (par de claves)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WalletAccount:
    """Identidad de un usuario en la billetera: id (dirección), clave pública y clave privada.

    NO contiene balance: el balance es estado del sistema y se consulta siempre al nodo
    mediante `WalletClient.get_balance(id)` justo antes de usarlo. De esta forma no existe
    una copia local que pueda quedar desactualizada.

    `private_key` se almacena solo en la billetera y nunca se transmite por la red.
    """

    id: str
    public_key: bytes
    private_key: bytes
