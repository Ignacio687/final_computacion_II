#!/bin/sh
set -eu
NODE_ID="${1:?node id required}"
shift
KEYS_DIR="/data/keys"
mkdir -p "${KEYS_DIR}"
if [ ! -f "${KEYS_DIR}/priv.pem" ]; then
  python - <<'PY'
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from main.infrastructure.serialization.canonical import derive_sender_id

keys_dir = Path("/data/keys")
private_key = Ed25519PrivateKey.generate()
keys_dir.mkdir(parents=True, exist_ok=True)
keys_dir.joinpath("priv.pem").write_bytes(
    private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
)
public_der = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
keys_dir.joinpath("pub.pem").write_bytes(
    private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
)
keys_dir.joinpath("mining_address.txt").write_text(derive_sender_id(public_der))
PY
fi
MINING_ADDRESS="$(cat "${KEYS_DIR}/mining_address.txt")"
exec python run.py node \
  --node-id "${NODE_ID}" \
  --mining-address "${MINING_ADDRESS}" \
  --private-key-path "${KEYS_DIR}/priv.pem" \
  --public-key-path "${KEYS_DIR}/pub.pem" \
  "$@"
