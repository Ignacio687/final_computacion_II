# Instrucciones de instalación y despliegue

HashCoin es una red blockchain educativa en Python. Este documento cubre instalación local,
ejecución manual de nodos/billetera y despliegue con Docker Compose.

## Requisitos

- Python 3.11 o superior
- `pip`
- Para Docker: Docker Engine y Docker Compose v2

## Instalación local

```bash
git clone <url-del-repositorio>
cd final_computacion_II
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # solo para tests
```

## Ejecución manual (desarrollo)

### Variables de entorno compartidas

Todos los nodos de una misma red deben usar la **misma** semilla de génesis y clave
simétrica precompartida:

```bash
export HASHCOIN_GENESIS_SEED="mi-semilla-compartida"
export HASHCOIN_SHARED_KEY="$(python -c 'import base64; print(base64.b64encode(b"\x00"*32).decode())')"
```

### Nodo

Generar claves Ed25519 del nodo (una vez por nodo) y calcular la dirección de minado
(`sha256` de la clave pública DER). Ejemplo mínimo con un solo nodo:

```bash
python run.py node \
  --node-id node1 \
  --bind-host 127.0.0.1 \
  --tcp-port 8001 \
  --http-port 9081 \
  --peers "" \
  --db-path ./node1.db \
  --difficulty 2 \
  --pow-workers 2 \
  --min-tx-per-block 3 \
  --block-interval-seconds 10 \
  --mining-reward 50 \
  --mining-address <DIRECCION_MINADO> \
  --private-key-path ./keys/node1/priv.pem \
  --public-key-path ./keys/node1/pub.pem \
  --genesis-prefund-accounts 5 \
  --genesis-prefund-amount 1000
```

Para una red de dos nodos, cada uno declara al otro en `--peers` (`host:puerto_tcp`).

### Billetera

Modo consola (consultas y envío manual):

```bash
python run.py wallet \
  --node-url http://127.0.0.1:9081 \
  --keys-dir ./wallet-keys
```

Modo generador de transacciones de prueba:

```bash
python run.py wallet \
  --node-url http://127.0.0.1:9081 \
  --keys-dir ./wallet-keys \
  --generator \
  --generator-users 5 \
  --generator-interval-seconds 2.0
```

El generador deriva las cuentas pre-fondeadas del génesis a partir de `HASHCOIN_GENESIS_SEED`
y envía solo transacciones con saldo suficiente.

## Tests

```bash
pytest -q
```

Con reporte de cobertura (requiere `requirements-dev.txt`):

```bash
pytest --cov=main --cov-report=term-missing
```

La configuración de `pytest.ini` añade el directorio raíz al `PYTHONPATH`.

## Despliegue con Docker Compose

La topología incluye **5 nodos** (CPUs distintas por servicio) y **1 billetera** en modo
generador. Las claves Ed25519 de cada nodo se generan automáticamente en el primer arranque
(`docker/entrypoint_node.sh`) y se guardan en el volumen `/data/keys` del contenedor.

Los valores por defecto de `.env.example` son **solo para laboratorio**. En producción
generar una semilla y una clave simétrica fuertes y no commitear `.env`.

```bash
cp .env.example .env
docker compose up --build
```

Puertos HTTP publicados al host (y accesibles entre contenedores):

| Servicio | TCP (nodos) | HTTP (host / red Docker) |
|----------|-------------|--------------------------|
| node1    | 8001        | 9081                     |
| node2    | 8002        | 9082                     |
| node3    | 8003        | 9083                     |
| node4    | 8004        | 9084                     |
| node5    | 8005        | 9085                     |

La billetera se conecta a `http://node1:9081` con fallback a `http://node3:9083` y genera
tráfico periódico para alimentar el mempool de la red.

Para detener y limpiar volúmenes:

```bash
docker compose down -v
```

## Verificación rápida

Con la red en marcha (local o Docker), consultar estado de un nodo:

```bash
curl "http://127.0.0.1:9081/status"
```

Respuesta esperada: JSON con `height`, `mempool_size`, `peers_connected` y `difficulty`.
