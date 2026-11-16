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
# Nodo 1 (logs en stderr; --bind-host auto = sockets IPv4+IPv6 nativos)
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

### Demo local (5 nodos, defensa IPv4/IPv6)

Para la mesa: **5 nodos locales** todos con `--bind-host auto`, peers mixtos `127.0.0.1` / `[::1]`, y chequeos `curl` por ambas familias:

```bash
./scripts/demo_local.sh
```

La defensa de IPv6 se hace en local; Docker Compose queda como demo multi-nodo en **IPv4** (contenedores). Detalle de red nativa abajo.

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

### Billetera con Docker

El compose levanta un servicio **`wallet`** en modo **generador** (envía txs automáticas a node1). No es interactivo; para verlo:

```bash
docker compose logs -f wallet
```

**Billetera interactiva** (comandos `status`, `send`, etc.) apuntando a los nodos del compose:

**Opción A — desde tu máquina** (la más simple; nodos en Docker, billetera local):

```bash
# Misma semilla que en .env
export HASHCOIN_GENESIS_SEED=hashcoin-docker-seed

python hashcoin.py wallet \
  --node-url http://127.0.0.1:9081 \
  --fallback-node-url http://127.0.0.1:9083
```

Dentro: `status`, `balance <addr>`, `send <from> <to> <amount>`, `help`.

**Opción B — dentro de un contenedor** (red interna Docker, claves en volumen `wallet-data`):

La imagen tiene `ENTRYPOINT ["python", "run.py"]`, así que `docker compose run` solo recibe los **args** del subcomando (mismo estilo que el `command:` del servicio `wallet` en compose):

```bash
docker compose run --rm -it wallet \
  wallet \
  --node-url http://node1:9081 \
  --fallback-node-url http://node3:9083 \
  --keys-dir /data/keys \
  --genesis-seed hashcoin-docker-seed
```

(`-it` es necesario para el prompt `wallet>`.)

**Solo consultar saldos / estado del nodo** sin billetera:

```bash
curl -s http://127.0.0.1:9081/status | python -m json.tool
curl -s "http://127.0.0.1:9081/balance?address=<dirección>"
```

Las cuentas con saldo inicial son las derivadas del génesis (`HASHCOIN_GENESIS_SEED`); `status` en la billetera las lista si usás la misma semilla.

**¿Por qué las cuentas génesis quedan en cero?** La moneda no desaparece:

- El **generador** del compose mueve fondos entre cuentas génesis, crea cuentas nuevas (~30 % de las txs) y paga **recompensas de minado** (50 por bloque) a direcciones de cada nodo.
- `status` muestra `total_supply (red)` = suma real en la blockchain (génesis + minado). Las 5 cuentas génesis suelen vaciarse; el saldo está en direcciones de minado y otras cuentas.
- Verificación: `curl -s http://127.0.0.1:9081/status` incluye `total_supply` (debe crecer con la altura de la cadena).

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

- **`--bind-host auto`** (default): escucha **nativa** con **dos sockets dedicados** por puerto (TCP y HTTP): `AF_INET` (IPv4) + `AF_INET6` con `IPV6_V6ONLY=1` (IPv6). No es un único socket dual-stack con IPv4 mapeado (`::ffff:`).
- Si en `auto` falla abrir el socket IPv6, el nodo **sigue en IPv4-only** y deja un **warning** en logs.
- Binds explícitos (`127.0.0.1`, `::1`, `0.0.0.0`, etc.) usan solo esa familia; un fallo de bind explícito aborta el arranque.
- Peers en CLI: `host:puerto` o **`[ipv6]:puerto`** (ej. `[::1]:8002`).
- Conexiones salientes resuelven hostname/IPv4/IPv6 automáticamente.

Ejemplos:

```bash
python hashcoin.py node start --bind-host auto
python hashcoin.py node start --bind-host 127.0.0.1   # solo loopback IPv4
python hashcoin.py node start --bind-host ::1        # solo loopback IPv6
python run.py node ... --peers "[::1]:8001,127.0.0.1:8002"
```

Demo one-shot de 5 nodos locales: `./scripts/demo_local.sh` (arriba). Compose no habilita IPv6 entre contenedores.

---

## Documentación extendida

- [`INSTALL.md`](INSTALL.md) — instalación y despliegue detallado
- [`README.md`](README.md) — visión del proyecto
- [`doc/protocolo.md`](doc/protocolo.md) — contrato técnico (no modificar sin acuerdo)
