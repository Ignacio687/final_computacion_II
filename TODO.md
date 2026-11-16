# Mejoras y características futuras

Lista de mejoras posibles para versiones posteriores al estado actual del proyecto (implementación completa + Docker Compose operativo).

## Validaciones de configuración

- Validar al arrancar el nodo que `--mining-address` sea una dirección con formato válido (id de cuenta derivable de una clave pública). Hoy se acepta cualquier string.
- Validar que `--peers` y conexiones HELLO entrantes usen el mismo criterio de identidad (hoy hay allowlist básica por `node_id` / host+puerto).

## Red y descubrimiento

- Descubrimiento automático de peers (hoy la lista se pasa por `--peers` en CLI o en `docker-compose.yml`).
- Usar `listen_port` del payload HELLO para reconexión dinámica (hoy se reconecta solo a la config estática).
- Reducir conexiones TCP duplicadas (incoming + outgoing) entre el mismo par de nodos.

## Observabilidad y operación

- Logging estructurado en handlers TCP/HTTP en lugar de tragar excepciones silenciosamente.
- Métricas básicas (bloques minados, txs rechazadas, peers desconectados) expuestas en `GET /status`.
- Healthchecks en todos los nodos del compose, no solo en `node1`.

## Seguridad (fuera del alcance educativo actual)

- TLS o canal autenticado adicional sobre TCP (hoy: clave simétrica precompartida + firmas Ed25519).
- Rotación de claves y secretos sin reiniciar toda la red.
- Rate limiting en endpoints HTTP y por peer TCP.

### Opcional: cifrado de canal por par de nodos (ECDH + AES)

Hoy el canal P2P usa `HASHCOIN_SHARED_KEY` (AES-GCM con clave simétrica idéntica en
toda la red) además de las firmas Ed25519 por nodo (PKI). Mejora posible sin TLS:

- **Opción B:** en el handshake (p. ej. ampliar `HELLO` o un mensaje posterior), cada par
  de nodos ejecuta un intercambio **ECDH** (p. ej. X25519 con `cryptography`) usando
  claves efímeras o derivadas del par Ed25519 del nodo.
- Derivar una **clave de sesión AES-256** por par `(node_id local, node_id remoto)` con
  HKDF a partir del secreto compartido ECDH.
- Cifrar los payloads TCP con esa clave de sesión (AES-GCM) en lugar de — o además de —
  la clave precompartida global.
- Mantener las **firmas Ed25519** del sobre para autenticidad e identidad del emisor.

Ventajas: no hace falta un secreto común en `.env`; compromiso de un nodo no expone el
tráfico con todos los demás. Coste: estado por peer, rotación/reconexión, y diseño del
handshake (documentar en `doc/protocolo.md` antes de implementar).

## Despliegue — ya implementado

Lo siguiente ya está en el repositorio; se documenta aquí como referencia, no como pendiente:

- `Dockerfile` con Python 3.12-slim y `ENTRYPOINT` a `run.py`.
- `docker-compose.yml` con 5 nodos (`cpus` distintas), billetera generadora, volúmenes por nodo y puertos HTTP `9081–9085` publicados al host.
- Claves Ed25519 de nodos generadas en runtime (`docker/entrypoint_node.sh`), no versionadas.
- Variables de entorno compartidas vía `.env` (plantilla en [`.env.example`](.env.example) en la raíz del repo).
- Pedido del profesor (IPv4/IPv6 **nativo**): **cumplido**. Con `--bind-host auto` el nodo abre sockets dedicados `AF_INET` + `AF_INET6` (`IPV6_V6ONLY=1` en el listener IPv6) para TCP y HTTP. Demo local de 5 nodos: `./scripts/demo_local.sh` (ver [`GUIA_USO.md`](GUIA_USO.md)).

Para levantar la red: `cp .env.example .env && docker compose up --build` (ver [`INSTALL.md`](INSTALL.md)).
