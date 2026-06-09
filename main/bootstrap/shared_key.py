"""Validación de la clave simétrica precompartida."""

import base64
import sys


def require_shared_key_b64(value: str | None) -> str:
    """Exige base64 válido que decodifique a exactamente 32 bytes."""
    if value is None or not str(value).strip():
        print(
            "Error: --shared-key o HASHCOIN_SHARED_KEY es obligatorio en modo node",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception:
        print(
            "Error: HASHCOIN_SHARED_KEY debe ser una cadena base64 válida",
            file=sys.stderr,
        )
        sys.exit(2)
    if len(decoded) != 32:
        print(
            f"Error: HASHCOIN_SHARED_KEY debe decodificar a 32 bytes "
            f"(obtenidos {len(decoded)})",
            file=sys.stderr,
        )
        sys.exit(2)
    return value
