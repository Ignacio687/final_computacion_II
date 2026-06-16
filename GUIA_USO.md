# Guía de uso — HashCoin

Guía corta para levantar, observar y probar la red localmente.

## Requisitos

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # solo para tests
```

Variables de entorno compartidas (misma red):

```bash
export HASHCOIN_GENESIS_SEED="hashcoin-docker-seed"
export HASHCOIN_SHARED_KEY="AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
```

(O `cp .env.example .env` para Docker.)

---

## Forma rápida: CLI `hashcoin`

```bash
# Nodo 1 (logs en stderr, dual-stack por defecto)
python hashcoin.py node start --verbose

# Nodo 2 (otra terminal)
python hashcoin.py node start --node-id node2 --tcp-port 8002 --http-port 9082 \
  --peers 127.0.0.1:8001

# Billetera interactiva
python hashcoin.py wallet --genesis-seed hashcoin-docker-seed
```

Dentro de la billetera:

| Comando | Qué hace |
|---------|----------|
| `status` | Nodo + cuentas con saldo, refresco cada 5 s (Ctrl+C para salir) |
| `status once` | Snapshot único |
| `balance <addr>` | Saldo de una dirección |
| `send <from> <to> <amount>` | Enviar transacción |
| `help` | Ayuda |

Ayuda argparse:

```bash
python hashcoin.py --help
python hashcoin.py node help
python hashcoin.py network          # comandos de ejemplo para 2 nodos
```

Parámetros útiles del nodo: `--difficulty`, `--pow-workers`, `--min-tx-per-block`, `--log-level`, `--bind-host auto`.

---

## Docker (5 nodos + billetera)

```bash
cp .env.example .env
docker compose up --build
```

| Nodo | HTTP (host) |
|------|-------------|
| node1 | http://127.0.0.1:9081/status |
| node2 | :9082 |
| node3 | :9083 |
| node4 | :9084 |
| node5 | :9085 |

```bash
curl -s http://127.0.0.1:9081/status | python -m json.tool
docker compose logs -f node1 node2
```

---

## Qué mirar (logs del nodo)

Con `--verbose` o `--log-level INFO` ves en stderr:

- `tcp: handshake ...` — conexión P2P
- `tcp: <- peer node2 NEW_TX` — mensaje entrante
- `propagation: tx aceptada en mempool`
- `mining: bloque minado block_id=...`
- `http: GET /status -> 200`

---

## Tests

```bash
pytest -q
pytest --cov=main --cov-report=term-missing
```

Integración (2 nodos en proceso): `tests/test_integration.py`, `tests/test_chain_sync.py`.

---

## Red: IPv4 / IPv6

- **`--bind-host auto`** (default): escucha dual-stack (`::` + IPv4 en Linux).
- Peers en CLI: `host:puerto` o **`[ipv6]:puerto`** (ej. `[::1]:8002`).
- Conexiones salientes resuelven hostname/IPv4/IPv6 automáticamente.

Ejemplos:

```bash
python hashcoin.py node start --bind-host auto
python hashcoin.py node start --bind-host 127.0.0.1   # solo loopback IPv4
python hashcoin.py node start --bind-host ::1        # solo loopback IPv6
python run.py node ... --peers "[::1]:8001,127.0.0.1:8002"
```

---

## Documentación extendida

- [`INSTALL.md`](INSTALL.md) — instalación y despliegue detallado
- [`README.md`](README.md) — visión del proyecto
- [`doc/protocolo.md`](doc/protocolo.md) — contrato técnico (no modificar sin acuerdo)
