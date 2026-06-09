#!/bin/sh
set -eu
NODE_ID="${1:?node id required}"
shift
MINING_ADDRESS="$(cat "/app/docker/keys/${NODE_ID}/mining_address.txt")"
exec python run.py node \
  --node-id "${NODE_ID}" \
  --mining-address "${MINING_ADDRESS}" \
  --private-key-path "/app/docker/keys/${NODE_ID}/priv.pem" \
  --public-key-path "/app/docker/keys/${NODE_ID}/pub.pem" \
  "$@"
