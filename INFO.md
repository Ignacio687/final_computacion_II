# Informe de decisiones de diseño

Breve resumen de las decisiones arquitectónicas de HashCoin y su justificación. El contrato
detallado está en [`doc/protocolo.md`](doc/protocolo.md).

## Modelo de datos

- **Transacciones** identificadas por `id = sha256(firmable + firma)`; direcciones (`sender_id`,
  `receiver_id`) como `sha256(clave_pública_DER)` en hex.
- **Bloques** encadenados por `last_hash`; el hash del bloque cumple PoW (SHA-256 con prefijo
  de ceros según `difficulty`). Una transacción **coinbase** por bloque paga `mining_reward` al
  minero.
- **Génesis determinista**: a partir de `genesis_seed` se construye el bloque 0 con
  transacciones `GENESIS` que pre-fondean cuentas derivadas de la misma semilla (§8). Todos los
  nodos con la misma semilla comparten el mismo génesis sin coordinación adicional.

## Persistencia

- **SQLite** por nodo (`blocks`, `transactions`, `mempool`). Cada nodo mantiene su copia local;
  la sincronización ocurre por TCP (`NEW_BLOCK`, `GET_CHAIN`/`CHAIN_RESPONSE`).
- Acceso serializado con locks por repositorio; lecturas de balance solo sobre transacciones
  confirmadas en cadena.

## Arquitectura por capas

- **Dominio**: modelos (`Transaction`, `Block`, mensajes).
- **Aplicación**: interfaces (`IBlockchainRepository`, `IMessageSender`, validadores, etc.).
- **Infraestructura**: adaptadores concretos (TCP, HTTP, SQLite, cripto, PoW).
- **Servicios**: orquestación de propagación, minado, consultas HTTP y envío de transacciones.
- **Bootstrap**: composición e inyección de dependencias en `node_bootstrap` y
  `wallet_bootstrap`.

## Comunicación

| Canal            | Protocolo | Uso |
|------------------|-----------|-----|
| Nodo ↔ Nodo      | TCP       | Mensajes firmados con payload cifrado (AES-256-GCM, clave precompartida). Handshake `HELLO` para identidad verificable. |
| Billetera → Nodo | HTTP/1.1  | REST mínimo (`GET /balance`, `/transactions`, `/status`; `POST /tx`). Implementado con `asyncio` en el nodo y `urllib` en la billetera. |
| Nodo → SQLite    | Archivo   | Persistencia inmediata al aceptar bloques/transacciones. |

No se usa TLS ni keepalive TCP: las reconexiones usan un delay fijo configurable.

## Concurrencia en el nodo

1. **asyncio** (proceso principal): acepta TCP/HTTP, propaga mensajes, coordina minado.
2. **ProcessPoolExecutor**: PoW fuera del event loop (`run_in_executor`).
3. **threading + queue.Queue** (`ChainVerificationDispatcher`): verificación pesada de cadenas
   sin bloquear el loop; el resultado se integra de forma thread-safe.

## Validación y consenso

- Transacciones validadas al entrar (firma, saldo, montos positivos). Coinbase y `GENESIS` no
  requieren firma de usuario.
- Bloques validados (encadenamiento, PoW, coinbase única con monto correcto, tx válidas).
- Cadena verificada contra el génesis esperado del `SeedGenesisProvider` local.
- Propagación **excepto al peer origen** para evitar bucles.

## Billetera

- `KeyStore` gestiona claves PEM y deriva cuentas del génesis para el generador de pruebas.
- `TransactionGenerator` consulta balances por HTTP y envía solo transacciones válidas.
- Modo consola interactivo para consultas y envío manual.

## Despliegue

- **Docker Compose**: 5 nodos con topología estática de peers (ver `doc/arquitectura.md`) y 1
  billetera generadora. `HASHCOIN_GENESIS_SEED` y `HASHCOIN_SHARED_KEY` unifican la red.
- Claves de nodo pre-generadas en `docker/keys/` (derivación determinista por `node_id`).
- CPUs limitadas por servicio para simular nodos heterogéneos.

## Dependencias

- Runtime: solo `cryptography` (Ed25519, AES-GCM, PEM/DER).
- Desarrollo/tests: `pytest`, `pytest-asyncio` (`requirements-dev.txt`).
- Resto: biblioteca estándar de Python 3.

## Pruebas

- Tests unitarios por contrato (`doc/plan_pruebas.md` §1).
- Dos integraciones clave en proceso: propagación de transacción (2.1) y minado con
  propagación de bloque entre dos nodos (2.2).
