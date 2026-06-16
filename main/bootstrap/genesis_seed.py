"""Validación de la semilla de génesis."""

import sys


def require_genesis_seed(value: str | None) -> str:
    """Exige semilla de génesis no vacía (CLI o HASHCOIN_GENESIS_SEED)."""
    if value is None or not str(value).strip():
        print(
            "Error: --genesis-seed o HASHCOIN_GENESIS_SEED es obligatorio en modo node",
            file=sys.stderr,
        )
        sys.exit(2)
    return str(value).strip()
