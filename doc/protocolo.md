# Protocolo canónico de HashCoin

Documento único de contratos. Fija, sin ambigüedad, cómo se serializan, identifican,
firman y cifran las entidades y los mensajes. Toda implementación (nodo y billetera)
debe respetar estas reglas al pie de la letra para que distintos procesos
interoperen y lleguen a los mismos hashes.

> Decisiones de alcance acordadas: firma **con handshake** (identidad verificable),
> **cifrado simétrico de payload con clave precompartida**, **fondeo por bloque génesis**,
> **sin keepalive** (reconexión con delay fijo).

---

## 1. Codificaciones base

- **Hash**: SHA-256, salida en **hex en minúsculas** (64 caracteres).
- **Bytes binarios en JSON** (firmas, claves públicas, clave de cifrado): **base64**
  estándar (RFC 4648, sin saltos de línea).
- **JSON canónico**: `json.dumps(obj, sort_keys=True, separators=(",", ":"))`,
  codificado en **UTF-8**. Se usa siempre que haya que firmar o hashear estructuras.
- **Timestamps**: **epoch en segundos como `float`** (UTC). `datetime` solo existe en el
  dominio en memoria; en DTO, persistencia y red siempre viaja como epoch. La conversión
  canónica es `datetime.fromtimestamp(ts, tz=timezone.utc)` y `dt.timestamp()`. Para
  hashear/firmar un bloque (§5.1) se usa **siempre el valor epoch float** (el mismo que
  viaja en el `BlockDTO`), nunca el `datetime`, para evitar diferencias de redondeo.

### 1.1 Algoritmo de firma (criptografía)

- **Firmas**: **Ed25519** (de la librería `cryptography`). Aplica tanto a las firmas de
  usuario (transacciones) como a las firmas de nodo (sobres TCP).
- **Claves en archivo**: PEM (`-----BEGIN PRIVATE KEY-----` / `PUBLIC KEY`).
- **`public_key` en transacciones y en HELLO**: bytes **DER** (SubjectPublicKeyInfo),
  obtenidos con `public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)`. La
  dirección (§2.1) se calcula sobre estos bytes DER.
- **`signature`**: bytes crudos que devuelve `Ed25519PrivateKey.sign(payload)`.
- **Cifrado de canal**: **AES-256-GCM** (`AESGCM` de `cryptography`) con la clave
  precompartida (§9).

---

## 2. Identidades

### 2.1 Dirección de usuario (`sender_id` / `receiver_id` / dirección)

```
address = sha256(public_key_DER).hexdigest()
```

donde `public_key_DER` son los bytes DER (SubjectPublicKeyInfo) de la clave pública del
usuario. Es determinista: misma clave pública ⇒ misma dirección.

### 2.2 Identidad de nodo (`node_id`)

Cadena arbitraria pasada por `--node-id`. Su clave pública se intercambia por **handshake**
(ver §6), no se deriva de `node_id`.

---

## 3. Transacción

Campos del dominio: `id`, `sender_id`, `receiver_id`, `amount` (int), `signature` (bytes),
`public_key` (bytes).

### 3.1 Bytes firmables

Lo que el usuario firma con su clave privada es el JSON canónico de los campos económicos
inmutables (NO incluye `id`, `signature` ni `public_key`):

```
firmable = json_canonico({
    "sender_id":   sender_id,
    "receiver_id": receiver_id,
    "amount":      amount
})
signature = sign(private_key, firmable)
```

### 3.2 `Transaction.id`

```
id = sha256(firmable + signature).hexdigest()
```

Incluir la firma garantiza un id único por transacción firmada.

### 3.3 Validez de una transacción (no-coinbase)

1. `sha256(public_key_DER) == sender_id`.
2. `verify(public_key, firmable, signature)` es verdadero.
3. `amount > 0`.
4. `id` recalculado coincide con el recibido.
5. Saldo suficiente: `balance(sender_id) >= amount` (ver §7 para el balance).

---

## 4. Transacciones especiales (sin firma)

Se identifican por su `sender_id` reservado. El validador **saltea** la verificación de
firma para ellas (`signature = b""`, `public_key = b""`).

### 4.1 Coinbase (recompensa de minado)

Exactamente **una** por bloque minado (no en el génesis):

```
sender_id   = "COINBASE"
receiver_id = mining_address
amount      = mining_reward
signature   = b""
public_key  = b""
id          = sha256(f"COINBASE|{altura}|{mining_address}|{mining_reward}").hexdigest()
```

### 4.2 Fondeo de génesis (`GENESIS`)

Ver §8. Igual forma que la coinbase pero `sender_id = "GENESIS"`.

---

## 5. Bloque

Campos del dominio: `id`, `last_hash`, `hash`, `timestamp`, `target`, `nonce`,
`transactions`.

- **`id`** = **altura** del bloque como entero (génesis = `0`, luego `1, 2, ...`). Es la
  clave de orden/persistencia. **No** es el hash. Al minar, `id = último_bloque.id + 1`.
- **`hash`** = hash PoW del bloque (ver abajo).
- **`target`** = cantidad de ceros hex iniciales requeridos en `hash` (dificultad).

### 5.0 Ensamblado del bloque candidato (al minar)

1. `id = get_last_block().id + 1`.
2. `last_hash = get_last_block().hash`.
3. `target = difficulty` configurada.
4. `timestamp = ahora` (UTC).
5. `transactions = [coinbase] + tx_del_mempool` en este orden: **la coinbase SIEMPRE
   primero**, seguida de las transacciones del mempool en **orden de inserción ascendente**
   (`get_mempool()`). Este orden es parte del contrato porque determina el hash.
6. Se busca `nonce` con PoW (§5.2).

### 5.1 Bytes hasheables y `hash`

```
hasheable = "|".join([
    last_hash,
    repr(timestamp_epoch),     # float epoch, p. ej. "1700000000.0"
    str(target),
    str(nonce),
    ",".join(tx.id for tx in transactions)   # ids en el orden del bloque
])
hash = sha256(hasheable.encode("utf-8")).hexdigest()
```

### 5.2 PoW

`hash` debe empezar con `target` caracteres `"0"`. Minar = buscar el `nonce` mínimo que lo
cumpla (resto de campos fijos).

### 5.3 Validez de un bloque

1. `block.last_hash == previous_hash` (hash del bloque previo en la cadena).
2. `block.hash` recalculado coincide y cumple el PoW para `block.target`.
3. `block.target == difficulty` configurada (dificultad esperada de la red).
4. Contiene **exactamente una** coinbase con `amount == mining_reward`.
5. Cada tx no-coinbase es válida (§3.3).
6. `block.timestamp > timestamp` del bloque previo.

### 5.4 Validez de una cadena (verificación pesada, en worker thread)

1. `blocks[0]` es **idéntico** al génesis esperado (mismo `id` y `hash`); el verificador
   recibe el `IGenesisProvider` para conocerlo.
2. Para todo `i > 0`: `blocks[i].last_hash == blocks[i-1].hash` y `blocks[i]` es válido (§5.3).
3. Ninguna tx (por `id`) se repite en toda la cadena.

---

## 6. Protocolo TCP entre nodos

### 6.1 Framing

`[4 bytes big-endian: longitud N][N bytes: sobre]`.

### 6.2 Sobre (envelope)

El sobre es un JSON con esta forma exacta:

```json
{
  "sender_node_id": "node-1",
  "type": "NEW_TX",
  "payload_cipher": "<base64 del payload cifrado>",
  "signature": "<base64 de la firma>"
}
```

- **`payload_cipher`**: el JSON canónico del payload (según el `type`), **cifrado** con la
  clave precompartida (§9), y luego base64.
- **`signature`**: firma del nodo emisor sobre el JSON canónico de
  `{"sender_node_id", "type", "payload_cipher"}`, en base64.

### 6.3 Recepción

1. Descifrar `payload_cipher` con la clave precompartida ⇒ JSON del payload.
2. Verificar `signature`:
   - Si `type == HELLO`: la clave pública aún no está registrada; se usa la `public_key`
     **que viene dentro del payload** ya descifrado (TOFU, §6.5).
   - Si `type != HELLO`: se usa la **clave pública del peer** registrada en el handshake.
     Si `sender_node_id` no está handshakeado o la firma falla ⇒ descartar la conexión.
3. Deserializar el payload a la dataclass correcta según `type` (mapeo estricto §6.4).

### 6.4 Mapeo estricto `type ↔ payload`

```
NEW_TX           -> NewTxPayload            (transaction: TransactionDTO)
NEW_BLOCK        -> NewBlockPayload         (block: BlockDTO)
GET_CHAIN        -> GetChainPayload         (since_height: int)
CHAIN_RESPONSE   -> ChainResponsePayload    (blocks: List[BlockDTO])
GET_MEMPOOL      -> GetMempoolPayload       (vacío)
MEMPOOL_RESPONSE -> MempoolResponsePayload  (transactions: List[TransactionDTO])
HELLO            -> HelloPayload            (handshake, §6.5)
```

Un `type` con un payload de forma incorrecta ⇒ se descarta el mensaje.

### 6.5 Handshake

Al abrir conexión, el iniciador envía primero un mensaje `HELLO`:

```
HelloPayload = { node_id: str, public_key: base64(DER), listen_port: int }
```

- El receptor registra `(node_id -> public_key)` y responde con su propio `HELLO`.
- Hasta no tener el `HELLO` del peer, no se aceptan otros mensajes de esa conexión.
- `listen_port` permite saber a qué puerto reconectar. La firma del `HELLO` se verifica
  contra la `public_key` que el mismo `HELLO` declara (confianza en primer uso / TOFU,
  suficiente para esta red local cerrada).

### 6.6 Reconexión (sin keepalive)

No hay PING/PONG. Si una conexión saliente se cae (error de socket / EOF), se reintenta
con un **delay fijo** `reconnect_delay_seconds` hasta restablecerla.

### 6.7 Repropagación

Al aceptar un `NEW_TX`/`NEW_BLOCK` recibido, se hace `broadcast(..., exclude_node_id=origen)`
para no devolvérselo al emisor. Igualmente, toda tx/bloque ya conocido (por `id`) se ignora,
de modo que un eventual reenvío redundante es inofensivo.

---

## 7. Balances

El balance de una dirección se calcula recorriendo las transacciones **confirmadas** (en
bloques de la cadena):

```
balance(addr) = sum(amount de tx donde receiver_id == addr)
              - sum(amount de tx donde sender_id == addr)
```

Las coinbase/génesis suman a su `receiver_id` y no restan de nadie.

---

## 8. Bloque génesis y fondeo inicial

`SeedGenesisProvider(seed, prefund_accounts, prefund_amount)` construye un génesis
**determinista** (bit a bit igual en todos los nodos dada la misma semilla):

- `id = 0`, `last_hash = "0"*64`, `target = 0`, `nonce = 0`, `timestamp = 0.0` (constante
  fija, para determinismo total).

- **Derivación de cuentas pre-fondeadas** (`i` de `0` a `prefund_accounts-1`):
  ```
  priv_seed_i = sha256(f"{seed}|prefund|{i}".encode("utf-8")).digest()   # 32 bytes
  priv_i      = Ed25519PrivateKey.from_private_bytes(priv_seed_i)
  pub_der_i   = priv_i.public_key().public_bytes(DER, SubjectPublicKeyInfo)
  address_i   = sha256(pub_der_i).hexdigest()
  ```

- **Transacciones de fondeo** (una por cuenta, en orden `i` ascendente):
  ```
  sender_id   = "GENESIS"
  receiver_id = address_i
  amount      = prefund_amount
  signature   = b""
  public_key  = b""
  id          = sha256(f"GENESIS|{i}|{address_i}|{prefund_amount}").hexdigest()
  ```

- `transactions` = esas txs `GENESIS` en orden `i` ascendente.
- `hash` = hash del bloque según §5.1 sobre esas transacciones.

La **billetera generadora**, dada la **misma semilla**, deriva exactamente las mismas
claves (mismo algoritmo) y por lo tanto puede firmar transacciones que gastan esos fondos
iniciales. Así el generador nunca produce transacciones inválidas por falta de saldo. El
validador de transacciones **saltea** la firma de las txs con `sender_id == "GENESIS"`
(igual que la coinbase, §4).

---

## 9. Cifrado del canal (clave precompartida)

- Todos los nodos comparten una **clave simétrica** (parámetro de despliegue
  `--shared-key`, idéntica en toda la red, base64 de 32 bytes).
- El `payload` de cada sobre TCP se cifra con esa clave (AES-GCM de la librería
  `cryptography`: nonce aleatorio de 12 bytes antepuesto al ciphertext, todo en base64).
- La **firma** (§6.2) sigue dando autenticidad/integridad por nodo; el cifrado da
  confidencialidad del canal. No se usa TLS.

---

## 10. HTTP billetera ↔ nodo

Endpoints (todas las respuestas son JSON con `Content-Type: application/json`):

- `GET /balance?address=<addr>` → `200 { "address": str, "balance": int }`
- `GET /transactions?address=<addr|opcional>&limit=<n>` → `200 [ TransactionDTO, ... ]`
  (orden cronológico descendente; `limit` por defecto 50).
- `GET /status` → `200 { "node_id": str, "height": int, "difficulty": int,
  "mempool_size": int, "peers_connected": int }`
- `POST /tx` (cuerpo: `TransactionDTO` firmada en JSON) →
  - `200 { "accepted": true,  "tx_id": str,  "error": null }`
  - `400 { "accepted": false, "tx_id": null, "error": "<motivo>" }` (JSON inválido,
    validación fallida o duplicada)
- Cualquier otra ruta/método → `404 { "error": "not found" }`.

### 10.1 Implementación del servidor HTTP del nodo

El nodo NO agrega dependencias web: `HTTPServer` se implementa sobre
**`asyncio.start_server`** con un parser mínimo de HTTP/1.1 (línea de request, headers,
body por `Content-Length`), corriendo en el **mismo event loop** que el resto del nodo
(así los handlers pueden `await` los servicios async, p. ej. `submit_transaction`).
Responde siempre con `Connection: close` (sin keep-alive). La **billetera** (cliente) usa
`urllib.request` de la stdlib. Es suficiente para la billetera/generador y los tests; no se
busca compatibilidad HTTP completa.

---

## 11. Persistencia SQLite (esquema)

Ambos repositorios (`SQLiteBlockchainRepository` y `SQLiteTransactionRepository`) usan el
**mismo archivo** `db_path` y crean las tablas si no existen (`CREATE TABLE IF NOT EXISTS`).
Esquema canónico:

```sql
-- Bloques de la cadena. id = altura.
CREATE TABLE IF NOT EXISTS blocks (
    id        INTEGER PRIMARY KEY,   -- altura del bloque
    last_hash TEXT NOT NULL,
    hash      TEXT NOT NULL UNIQUE,
    timestamp REAL NOT NULL,         -- epoch float UTC
    target    INTEGER NOT NULL,
    nonce     INTEGER NOT NULL
);

-- Transacciones confirmadas (incluidas en un bloque). signature/public_key en base64.
CREATE TABLE IF NOT EXISTS transactions (
    id          TEXT PRIMARY KEY,
    block_id    INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,    -- orden dentro del bloque (0 = coinbase/primera)
    sender_id   TEXT NOT NULL,
    receiver_id TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    signature   TEXT NOT NULL,       -- base64 ("" para coinbase/génesis)
    public_key  TEXT NOT NULL        -- base64 ("" para coinbase/génesis)
);

-- Mempool (transacciones pendientes, aún no confirmadas).
CREATE TABLE IF NOT EXISTS mempool (
    id          TEXT PRIMARY KEY,
    seq         INTEGER NOT NULL,    -- orden de inserción (AUTOINCREMENT lógico)
    sender_id   TEXT NOT NULL,
    receiver_id TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    signature   TEXT NOT NULL,
    public_key  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tx_sender   ON transactions(sender_id);
CREATE INDEX IF NOT EXISTS idx_tx_receiver ON transactions(receiver_id);
CREATE INDEX IF NOT EXISTS idx_tx_block    ON transactions(block_id);
```

Reglas:
- `append_block(block)` inserta la fila en `blocks` y todas sus tx en `transactions`
  (con `position` según el orden del bloque), y borra del `mempool` las tx ya confirmadas.
- `replace_chain(blocks)` reemplaza atómicamente (en una transacción SQL) el contenido de
  `blocks` y `transactions`; el mempool se reconcilia (las tx que quedaron fuera de la
  nueva cadena y siguen siendo válidas vuelven/permanecen en mempool).
- `get_balance` / `get_transactions_*` se calculan **solo** sobre `transactions`
  (confirmadas), nunca sobre `mempool` (ver §7).
- `exists_in_mempool_or_chain(id)` consulta ambas tablas `mempool` y `transactions`.
- Abrir cada conexión con `PRAGMA foreign_keys = ON`. Acceso serializado con un lock por
  repositorio (SQLite + asyncio/threads).
