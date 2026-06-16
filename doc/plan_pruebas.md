# Plan de pruebas

Define la batería mínima de tests para validar los contratos de `doc/protocolo.md`. Pensado
para que un agente lo implemente sin decisiones abiertas. Framework: **pytest** (+
`pytest-asyncio` para los tests async). Estructura: carpeta `tests/` en la raíz.

Ejecutar:

```bash
pip install -r requirements-dev.txt
pytest -q
```

Convenciones de fixtures para tests:
- `genesis_seed = "test-seed"`, `shared_key` = base64 de 32 bytes fijos (p. ej. `b"\x00"*32`).
- `difficulty = 1` (PoW casi instantáneo), `mining_reward = 50`,
  `genesis_prefund_accounts = 3`, `genesis_prefund_amount = 1000`.
- Puertos efímeros (`0`) o un rango alto fijo; `db_path` en `tmp_path` (SQLite por test).

---

## 1. Tests unitarios (por contrato)

### 1.1 Cripto (`ISigner`/`IVerifier`, §1.1)
- `sign` + `verify` round-trip con Ed25519 devuelve True.
- `verify` con firma alterada o clave pública distinta devuelve False (no lanza).
- `get_public_key` devuelve DER cargable por `load_der_public_key`.

### 1.2 Direcciones e IDs (§2, §3)
- `sender_id` = `sha256(public_key_DER)` es determinista para la misma clave.
- Bytes firmables = `json_canonico({sender_id, receiver_id, amount})` (claves ordenadas).
- `Transaction.id` = `sha256(firmable + signature)` reproducible.

### 1.3 Mappers DTO <-> dominio (§1, §3-§5)
- `transaction_to_dto`/`transaction_from_dto` round-trip (signature/public_key base64).
- `block_to_dto`/`block_from_dto` round-trip (timestamp datetime <-> epoch float, tx anidadas).

### 1.4 Validación de transacción (`ITransactionValidator`, §3.3)
- Tx bien firmada y con saldo suficiente → válida.
- Firma inválida → inválida. `sender_id` que no deriva de `public_key` → inválida.
- `amount <= 0` → inválida. Saldo insuficiente → inválida.
- Coinbase/`GENESIS` (sin firma) → no se les exige firma.

### 1.5 PoW (`IProofOfWork`, §5.2)
- `mine(candidate)` devuelve un hash que empieza con `target` ceros y `verify(block)` True.
- `verify` con hash/nonce manipulado → False.

### 1.6 Validación de bloque y cadena (§5.3, §5.4)
- Bloque válido (encadena, PoW ok, una coinbase con `mining_reward`, tx válidas) → True.
- Casos negativos: `last_hash` incorrecto, target distinto al esperado, sin coinbase o con
  monto de coinbase incorrecto, timestamp no creciente.
- `verify_chain`: cadena correcta → True; génesis distinto al esperado → False; eslabón
  roto (`last_hash` no encadena) → False; tx duplicada en la cadena → False.

### 1.7 Génesis determinista (§8)
- Dos `SeedGenesisProvider` con la misma semilla producen bloques con el **mismo hash**.
- Semillas distintas → hashes distintos.
- `KeyStore.derive_genesis_accounts(seed, N)` produce las direcciones que el génesis
  fondea (los `receiver_id` de las txs `GENESIS` coinciden), y esas claves pueden firmar.

### 1.8 Codec de mensajes (`MessageCodec`, §6)
- `encode` + `decode` round-trip para cada `MessageType` (payload igual al original).
- Firma alterada en el sobre → `decode` lanza/rechaza.
- `HELLO` se decodifica usando la `public_key` del propio payload (sin clave previa).
- Mapeo estricto: un `type` con payload de forma incorrecta → `decode` rechaza.

### 1.9 Repositorios SQLite (§7, §11)
- `append_block` persiste bloque + tx y limpia mempool; `get_chain`/`get_last_block`/
  `get_height` consistentes.
- `get_balance` calcula sobre confirmadas (coinbase/GENESIS suman; envíos restan).
- `exists_in_mempool_or_chain` detecta en ambas tablas.
- `replace_chain` reemplaza atómicamente.

---

## 2. Tests de integración (acotados a 2 escenarios clave)

Levantan **2 nodos en el mismo proceso** (event loop de asyncio), con la misma
`shared_key`, `genesis_seed` y `difficulty=1`, peers cruzados, y `db_path` temporal por
nodo. Se espera con polling breve (no `sleep` fijos largos) a que se cumpla la condición.

### 2.1 Propagación de transacción (HTTP + TCP + handshake + codec)
1. Arrancar Nodo A y Nodo B (B en los peers de A y viceversa); esperar handshake.
2. Construir una tx firmada desde una cuenta pre-fondeada del génesis (saldo > 0).
3. `POST /tx` al Nodo A → respuesta `200 {"accepted": true}`.
4. **Aserción**: en un tiempo acotado, la tx aparece en el mempool del Nodo B
   (vía repositorio o `GET /transactions`/estado), y no se duplica.

### 2.2 Minado y propagación de bloque (PoW + NEW_BLOCK + validación)
1. Con la tx anterior en mempool y `min_transactions_per_block` alcanzado, el Nodo A mina.
2. **Aserción**: el Nodo B recibe `NEW_BLOCK`, lo valida y lo añade
   (`get_height` del B aumenta y su `get_last_block().hash` == el del A).
3. **Aserción**: el balance del receptor de la tx aumenta en ambos nodos (consulta a la
   cadena confirmada); el de la `mining_address` aumenta en `mining_reward`.

> Nota: la sincronización por `GET_CHAIN`/`CHAIN_RESPONSE` (reemplazo de cadena más larga)
> queda fuera de los 2 escenarios mínimos; el verificador de cadena se cubre en 1.6.
