"""Cuenta con saldo y última actividad en la cadena confirmada."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ActiveAccount:
    address: str
    balance: int
    last_block_id: int
