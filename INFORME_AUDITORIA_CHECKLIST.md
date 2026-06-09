# Informe de auditoría (checklist)

Checklist derivado del análisis exhaustivo de código y documentación, orientado a dejar el proyecto listo para delegar implementación a agentes sin divergencias de contrato.

> **Estado (fase de contratos cerrada).** Se fijaron todos los contratos en código y se
> sincronizaron documentación y diagramas. El contrato canónico único está en
> [`doc/protocolo.md`](doc/protocolo.md). Decisiones de alcance acordadas: firma **con
> handshake** (identidad verificable), **cifrado simétrico de payload con clave
> precompartida**, **fondeo por bloque génesis**, **sin keepalive** (reconexión con delay
> fijo), **tests de integración acotados**. Lo que queda (marcado abajo) pertenece a la
> fase de **implementación**.

---

## 1) Bloqueantes (rompen integración entre agentes)

- [x] `broadcast` excluye al peer origen vía `broadcast(message, exclude_node_id=...)` en `IMessageSender`.
- [x] Verificación de firmas TCP: la clave pública del peer se obtiene en el handshake `HELLO` (protocolo §6.5); `MessageCodec` verifica cada sobre.
- [x] La verificación de cadena referencia el génesis esperado (`DefaultChainVerifier(block_validator, genesis_provider)`).
- [x] Validación de bloque con dependencias: `DefaultBlockValidator(proof_of_work, transaction_validator, expected_difficulty, mining_reward)`.
- [x] Transacción coinbase especificada (protocolo §4.1).
- [x] Serialización canónica de transacción firmable (protocolo §3.1).
- [x] Serialización canónica de bloque hasheable (protocolo §5.1).
- [x] Derivación canónica de `sender_id` desde `public_key` (protocolo §2.1).
- [x] Algoritmo canónico para `Transaction.id` (protocolo §3.2).
- [x] Formato exacto del sobre TCP firmado + cifrado (protocolo §6.2-§6.4).
- [x] Documentación de cifrado alineada: clave simétrica precompartida (AES-GCM), sin TLS (protocolo §9; docs actualizadas).
- [x] Componente de cola + workers declarado: `ChainVerificationDispatcher` (`queue.Queue` + threading).
- [x] Componentes de billetera declarados: `KeyStore`, `WalletConsole`, `TransactionGenerator`, `tx_builder`.
- [x] Mappers DTO <-> dominio declarados (`repository/dto/mappers.py`).
- [x] `peers_connected` resuelto sin romper DIP: `IMessageSender.connected_count()` inyectado en `WalletQueryService`.
- [x] Handshake/identificación definido (`HELLO`: `node_id`, `public_key`, `listen_port`; protocolo §6.5).
- [x] PING/PONG eliminado (keepalive fuera de alcance); reconexión con delay fijo (`reconnect_delay_seconds`).
- [x] Wiring `HTTPHandlers`/`TCPMessageHandler`/bootstrap alineado (`HTTPServer(handlers)`, pseudocódigo de bootstrap actualizado).
- [x] Estrategia de fondeo inicial: génesis pre-fondea cuentas derivadas de la semilla (protocolo §8).

---

## 2) Inconsistencias importantes de documentación

- [x] `Block.id` = altura; `Block.hash` = hash PoW (protocolo §5; modelos/DTO actualizados).
- [x] Cantidad de nodos unificada a **4-5** en toda la documentación.
- [x] Protocolo billetera <-> nodo unificado a **HTTP**.
- [x] Topología del ASCII alineada con `diagramas/arquitectura/arquitectura.mmd`.
- [x] Flujo de bloque separa aceptación de `NEW_BLOCK` del reemplazo por `CHAIN_RESPONSE`.
- [x] `diagramas/entidad/entidad.mmd` corregido (`Transaction`, `NodeInfo`, `WalletAccount`).
- [x] `diagramas/clase/clase.mmd` actualizado al diseño por capas real.
- [x] Argumentos reales de `run.py` reflejados (CLI actualizada; ver §10 y ejemplos en `run.py`).
- [x] `--genesis-seed` (y `--shared-key`) soportan variable de entorno (`HASHCOIN_GENESIS_SEED`, `HASHCOIN_SHARED_KEY`).

---

## 3) Deuda técnica / huecos declarativos (no bloqueantes inmediatos)

- [x] `Account` removido (se conserva `WalletAccount`).
- [x] Mapeo estricto `MessageType` <-> `Payload` documentado y delegado a `MessageCodec.decode` (protocolo §6.4).
- [x] Cuerpo de respuesta estándar para `POST /tx` definido (protocolo §10; docstring de `handle_post_tx`).
- [x] Frontera repositorio de cadena vs transacciones aclarada (docstring de `ITransactionRepository`).
- [x] Conversión `datetime` <-> epoch canónica (protocolo §1).
- [x] Diagramas de flujo indican repropagación "excepto origen".
- [x] Pseudocódigo de bootstrap completado con dependencias reales finales.
- [ ] Completar `INSTALL.md` — **fase de implementación** (depende de Dockerfile/compose).
- [ ] Completar `INFO.md` — **fase de implementación**.
- [x] Dependencias declaradas (`requirements.txt`: solo `cryptography`).
- [x] Batería de tests **definida** en [`doc/plan_pruebas.md`](doc/plan_pruebas.md) (unitarios por contrato + 2 integraciones clave). Su **implementación** queda para la fase de código.

---

## 4) Recomendaciones de implementación (orden sugerido)

- [x] Interfaces actualizadas (`IMessageSender`, validador de bloque, verificador de cadena, etc.).
- [x] Protocolo canónico documentado en un documento único (`doc/protocolo.md`).
- [x] Componentes estructurales agregados (dispatcher de verificación, mappers, codec, módulos de wallet).
- [x] Bootstrap con dependencias inyectadas de forma explícita.
- [x] Diagramas Mermaid regenerados a partir del contrato final.
- [ ] Delegar por bloques a agentes — **siguiente fase**.

---

## 5) Estado de preparación para delegar

- [x] Contratos cerrados (serialización/firma/IDs sin ambigüedades).
- [x] Algoritmos cripto fijados (Ed25519 + AES-GCM; claves DER/PEM; §1.1).
- [x] Protocolo TCP definido end-to-end (identidad por handshake + firma verificable, decode de HELLO).
- [x] Consenso/validación de bloque y cadena cerrados (incl. orden de tx y target esperado).
- [x] Minado + coinbase canónicos (ensamblado de bloque §5.0).
- [x] Génesis determinista con derivación exacta de cuentas pre-fondeadas (§8).
- [x] Esquema SQLite definido (§11) y servidor HTTP especificado (§10.1, sin dependencias web).
- [x] Plan de pruebas definido (`doc/plan_pruebas.md`) y dependencias dev declaradas.
- [x] Documentación y diagramas consistentes con el código declarado.

> **Listo para delegar la implementación por bloques.** Pendiente solo de la fase de
> implementación: escribir el código de los stubs, los tests, y `INSTALL.md`/`INFO.md`/Docker.
