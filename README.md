# Proyecto integrador — Computación II

Repositorio del trabajo práctico integrador para el examen final de la materia **Computación II**. Contiene la documentación del proyecto, el código de la aplicación y las instrucciones para instalación y uso.

---

## Alumno

**Ignacio Chaves** — Legajo: 61.220

---

## Qué es y para qué sirve

Este proyecto es una aplicación que pone en práctica los contenidos de la materia (sockets, concurrencia, IPC, asincronismo, colas de tareas, etc.). El tema y alcance se acordaron con la cátedra; la documentación en `doc/` y `final/` define la arquitectura y funcionalidades.

*(Breve descripción de qué hace la aplicación.)*

---

## Documentación y ejecución

| Documento | Contenido |
|-----------|-----------|
| [**doc/**](doc/) | Definición del proyecto: descripción verbal, arquitectura y funcionalidades por entidad (acordado con la cátedra). Incluye [**protocolo.md**](doc/protocolo.md) (contrato canónico único: serialización, firma, cifrado, IDs, génesis, esquema SQLite) y [**plan_pruebas.md**](doc/plan_pruebas.md). |
| [**final/**](final/) | Detalles conceptuales e ideas de implementación (diagramas, etc.). |
| [**diagramas/**](diagramas/) | Diagramas Mermaid: arquitectura, clase, entidad, flujo y secuencia. |
| [**INSTALL.md**](INSTALL.md) | Cómo clonar, instalar y ejecutar (o desplegar) la aplicación. |
| [**GUIA_USO.md**](GUIA_USO.md) | Guía corta: comandos, pruebas, logs, IPv4/IPv6. |
| [**INFO.md**](INFO.md) | Decisiones de diseño y justificación (modelo de datos, concurrencia, almacenamiento, etc.). |
| [**TODO.md**](TODO.md) | Mejoras y características previstas para futuras versiones. |

---

## Uso básico de la aplicación

### Uso rápido con hashcoin

CLI amigable para desarrollo local (delega en `run.py` sin duplicar bootstrap):

```bash
# Nodo con defaults (puertos 8001/9081, datos en ./data/node1/)
python hashcoin.py node start

# O con el script ejecutable en la raíz del repo:
chmod +x hashcoin    # una vez
./hashcoin node start

# Segundo nodo enlazado al primero
python hashcoin.py node start --node-id node2 --tcp-port 8002 --http-port 9082 \
  --peers 127.0.0.1:8001

# Billetera interactiva
python hashcoin.py wallet

# Generador de transacciones de prueba
python hashcoin.py wallet --generator --generator-users 5

# Ejemplos de red local y ayuda detallada
python hashcoin.py network
python hashcoin.py node help
python hashcoin.py --help
```

Parámetros expuestos en `node start` (requisitos cátedra): `--difficulty`,
`--pow-workers`, `--min-tx-per-block`, `--block-interval-seconds`, `--mining-reward`,
`--log-level` (reservado). Secretos compartidos vía `HASHCOIN_GENESIS_SEED` y
`HASHCOIN_SHARED_KEY` (defaults de laboratorio en `.env.example`).

Para flags completos y despliegue Docker, ver [INSTALL.md](INSTALL.md). Guía rápida de comandos y pruebas: [GUIA_USO.md](GUIA_USO.md).

### Uso directo con run.py

```bash
python run.py node --node-id node1 --tcp-port 8001 --http-port 9081 ...
python run.py wallet --node-url http://127.0.0.1:9081 --keys-dir ./wallet-keys
```

---

## Requisitos de la materia

El trabajo debe incluir, entre otros aspectos: sockets con clientes concurrentes, mecanismos de IPC, asincronismo de I/O, cola de tareas distribuidas y parseo de argumentos por línea de comandos. Detalle completo en [REQUISITOS.md](REQUISITOS.md).
