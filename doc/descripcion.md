# Descripción verbal de la aplicación

HashCoin es una aplicación **distribuida tipo blockchain mínima**: varios **nodos** mantienen una cadena de bloques en común y un pool de transacciones pendientes (mempool). Se comunican entre sí por **TCP** con mensajes **JSON cifrados y firmados**. Cada nodo expone además un **servidor HTTP** estándar para que clientes (la **billetera** u otros) consulten estado y envíen transacciones. La **billetera** es un cliente opcional que, por consola, permite ver balance y transacciones y actuar como **generador de transacciones de prueba** (usuarios y transacciones aleatorios) para que la red tenga trabajo sin usuarios reales.

---

## Tipo de aplicación y roles

- **Modelo**: red P2P de nodos (servidores entre sí) + clientes HTTP (billetera u otros) que hablan con los nodos.
- **Nodos**: actúan como **servidores** ante otros nodos (protocolo TCP propio) y ante la billetera/CLI (HTTP). A la vez son **clientes** de sus peers cuando propagan mensajes o piden la cadena.
- **Billetera**: **cliente** HTTP de uno o más nodos; genera transacciones de prueba aleatorias para alimentar la red.

No hay “un” servidor central: la red es descentralizada; cada nodo es par de los demás.

---

## Qué hace cada parte (resumen)

- **Nodo**: Mantiene blockchain y mempool en memoria y en **SQLite**. Escucha en dos puertos: uno para **TCP** (protocolo entre nodos) y otro para **HTTP** (consultas y envío de transacciones). Valida transacciones y bloques (firmas, integridad, reglas de negocio). **Propaga** transacciones y bloques a sus peers por TCP. Realiza **PoW** (minado) usando un pool de procesos (**ProcessPoolExecutor**) desde asyncio con `run_in_executor`; para tareas como verificación pesada de cadenas se usan **cola y workers en hilos** (`queue.Queue` + `threading`). Persiste cada bloque y transacción aceptada al vuelo. Si recibe una cadena más larga y válida, reemplaza la local (regla de la cadena más larga).
- **Billetera**: Cliente por **consola**. Por HTTP consulta a un nodo (balance, transacciones, estado) y envía transacciones (POST). Para **probar el sistema** sin usuarios reales, la billetera incluye (o se acompaña de) un **generador** que crea usuarios y transacciones aleatorias y las envía al nodo, de modo que los nodos tengan trabajo constante.
- **Usuario**: Entidad lógica identificada por par de claves (PKI); las transacciones van firmadas. En las pruebas, los “usuarios” son generados aleatoriamente (claves, direcciones, montos).

---

## Concurrencia, paralelismo y comunicación asincrónica

- **Asincronismo de I/O**: Cada nodo usa **asyncio** para atender muchas conexiones TCP (otros nodos) y muchas peticiones HTTP (billetera, etc.) a la vez sin bloquear. Un único event loop maneja aceptar conexiones, leer y escribir mensajes.
- **Paralelismo (PoW)**: El minado es CPU-bound. Se hace en un **ProcessPoolExecutor**; el proceso principal (asyncio) envía el trabajo con `run_in_executor` y recibe el resultado sin bloquear el loop.
- **Threading y cola de tareas**: Para tareas como verificación de cadenas largas se usan **queue.Queue** y **workers** en hilos (`threading`): el proceso principal encola tareas, los workers las procesan y devuelven resultados por otra cola; el resultado se integra en el flujo asyncio vía un thread que notifica al loop.
- **Sincronización**: Donde se comparta estado (mempool, blockchain en memoria) entre tareas asyncio o entre procesos, se usan **locks** o estructuras thread-safe para evitar condiciones de carrera.
- **Concurrencia de clientes**: Tanto las conexiones TCP entre nodos como las HTTP se atienden de forma concurrente en el mismo nodo gracias a asyncio (y, en HTTP, un servidor que delegue en asyncio o hilos según se implemente).

---

## Protocolos y datos

- **Entre nodos (TCP)**  
  Mensajes en **JSON**, con **firma** (integridad y autenticación) y **cifrado** (canal o payload; en implementación se puede usar TLS para el canal). Formato: longitud (4 bytes) + cuerpo (JSON cifrado/firmado). Tipos de mensaje: **NEW_TX**, **NEW_BLOCK**, **GET_CHAIN**, **CHAIN_RESPONSE**, **GET_MEMPOOL**, **MEMPOOL_RESPONSE**, **PING**, **PONG**. **PING/PONG** sirven como keepalive: el nodo envía PING periódicamente al peer; si no recibe PONG dentro de un timeout, considera la conexión caída y la cierra para intentar reconectar; así se detectan peers caídos sin depender solo del cierre de socket.
- **Billetera ↔ Nodo (HTTP)**  
  Cada nodo es un servidor HTTP estándar. La billetera hace GET para consultas (balance, transacciones, estado) y POST para enviar transacciones. Ejemplos: `GET /balance?address=...`, `GET /transactions`, `POST /tx` con el cuerpo firmado.
- **Transacción**: campos como `id`, `sender_id`, `receiver_id`, `amount` (entero), `signature`, `public_key` (y los que se definan en el modelo).
- **Bloque**: `id`, `last_hash`, `hash`, `timestamp`, `target` (dificultad), `nonce`, lista de transacciones. La **dificultad** del PoW es **configurable por argumentos de línea de comando**.

---

## Bloque génesis y datos de prueba

- **Bloque génesis**: Un generador produce una **semilla aleatoria** (cadena o estructura) que se usa para crear el primer bloque común. Todos los nodos arrancan con el mismo bloque génesis para compartir la misma base de cadena.
- **Usuarios y transacciones de prueba**: Para correr y probar el sistema no hay usuarios reales. Un **generador** (integrado en la billetera o como herramienta aparte) crea de forma aleatoria usuarios (pares de claves) y transacciones entre ellos, y las envía a los nodos vía HTTP. Así la billetera “alimenta” la red y los nodos procesan y minan bloques.

---

## Parseo por línea de comando

Se usa **argparse** desde el inicio. Argumentos del nodo: puerto TCP, puerto HTTP, lista de peers (opcional para descubrimiento automático a futuro), ruta de BD SQLite, dificultad del PoW, cantidad de workers del pool de procesos. Argumentos de la billetera: URL del nodo, modo “generador” de transacciones de prueba.

---

## Despliegue

**Docker Compose** con 4–5 nodos (cada uno con distinta configuración de núcleos asignados) y 1 billetera, todo en local en la misma máquina. Los nodos con más núcleos asignados minan más bloques; la verificación criptográfica y el consenso (cadena más larga) impiden alterar transacciones.

El detalle de arquitectura (nodos, conectividad, IPC) y la lista de funcionalidades por entidad están en **arquitectura.md** y **funcionalidades.md**.
