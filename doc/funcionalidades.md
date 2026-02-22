# Funcionalidades por entidad

Listado de responsabilidades y acciones de cada componente. Los diagramas de clase, entidad, flujo y secuencia están en [**diagramas/**](../diagramas/).

---

## Nodo

- **Iniciar y configurar**
  - Leer argumentos con **argparse** (puerto TCP, puerto HTTP, lista de peers, ruta SQLite, dificultad, workers del pool, etc.).
  - Cargar bloque génesis (mismo para todos; semilla desde generador).
  - Cargar blockchain y mempool desde SQLite si existe; si no, iniciar con el génesis.
  - Iniciar event loop asyncio, servidor TCP (protocolo entre nodos) y servidor HTTP (billetera/CLI).

- **Atender conexiones TCP (peers)**
  - Aceptar conexiones entrantes de otros nodos.
  - Recibir mensajes (longitud + JSON cifrado/firmado), deserializar y verificar firma/cifrado.
  - Según tipo: **NEW_TX** → validar transacción, añadir a mempool, persistir, reenviar a otros peers; **NEW_BLOCK** → validar bloque, si es válido añadir a cadena, actualizar mempool, persistir, reenviar; **GET_CHAIN** → responder **CHAIN_RESPONSE**; **GET_MEMPOOL** → **MEMPOOL_RESPONSE**; **PING** → **PONG**.
  - Enviar mensajes a peers (propagación, respuestas). Mantener una conexión TCP persistente con cada peer; ante caída de conexión (cierre inesperado o timeout sin PONG), cerrar y reconectar con backoff exponencial.

- **Atender HTTP (billetera / clientes)**
  - **GET** consultas: balance por dirección, transacciones (o últimas de la cadena), estado (altura, dificultad, etc.).
  - **POST** transacción: recibir transacción firmada, validar, añadir a mempool, persistir, propagar por TCP a peers.

- **Minar (PoW)**
  - Cuando se alcance un número de transacciones en mempool o un intervalo de tiempo configurado: armar bloque candidato (transacciones del mempool + recompensa de minado), enviar trabajo al **ProcessPoolExecutor** vía `run_in_executor`, recibir nonce/hash cuando termine.
  - Firmar/armar mensaje **NEW_BLOCK** y enviarlo por TCP a todos los peers.
  - Añadir bloque a la cadena local, actualizar mempool, persistir.

- **Sincronización de cadena**
  - Si llega **CHAIN_RESPONSE** con cadena más larga y válida: reemplazar cadena local, actualizar mempool, persistir.
  - Opcional: pedir cadena al conectar a un peer si la local está vacía o detrás (GET_CHAIN).

- **Verificación de cadena (threading)**
  - Tareas pesadas como verificación de cadenas se encolan en **queue.Queue**; workers en hilos (`threading`) procesan y devuelven el resultado por otra cola; el resultado se integra en el flujo asyncio (vía thread que notifica al loop).

- **Persistencia**
  - Escribir en SQLite cada bloque añadido y cada transacción aceptada al mempool (o al confirmarse); leer al arrancar para reconstruir estado.

---

## Billetera

- **Iniciar y configurar**
  - **argparse**: URL del nodo (o lista), modo “solo consulta” vs “generador de transacciones de prueba”, etc.
  - Conectarse por HTTP al nodo indicado.

- **Consultas (usuario final)**
  - Mostrar por consola: balance de una dirección, historial de transacciones (leyendo del nodo vía GET).
  - Permitir elegir dirección (o par de claves cargado/generado) para consultas.

- **Enviar transacción**
  - Construir transacción (remitente, destinatario, monto), firmar con clave privada del “usuario”, enviar al nodo por POST /tx.

- **Modo generador de transacciones de prueba**
  - Generar usuarios aleatorios (pares de claves) y transacciones entre ellos (montos, firmas).
  - Enviar transacciones al nodo por HTTP de forma periódica o bajo demanda, para que la red tenga trabajo sin usuarios reales.
  - Opcional: leer direcciones/balances del nodo para que las transacciones de prueba sean coherentes (no gastar más de lo que hay).

---

## Usuario (entidad lógica)

- No es un proceso; es la identidad asociada a un par de claves (PKI).
- **Crear transacciones**: firmar con su clave privada (desde billetera o herramienta CLI).
- **Recibir y verificar**: las transacciones que lo involucran se validan en los nodos usando la clave pública y la firma.
- En las pruebas, los “usuarios” son creados por el **generador** (billetera o script) con claves aleatorias.

---

## Generador de bloque génesis

- **Responsabilidad**: Producir una **semilla aleatoria** (cadena o estructura) y, a partir de ella, el **bloque génesis** común para toda la red.
- **Uso**: Al iniciar el primer nodo (o en un script de inicialización), se ejecuta el generador; el bloque resultante se guarda y se comparte (archivo, o mismo binario/script en todos los nodos) para que todos arranquen con la misma cadena base.
- Puede ser un módulo o script aparte, invocado una vez o integrado en el arranque del nodo cuando no existe aún la BD.

---

## Generador de usuarios y transacciones de prueba

- **Responsabilidad**: Crear datos de prueba para que la red tenga actividad: usuarios (pares de claves) y transacciones firmadas entre ellos.
- **Ubicación**: Integrado en la **billetera** (modo “generador”) y/o como script/herramienta aparte que envía transacciones por HTTP a un nodo.
- **Funciones**: Generar N direcciones (claves); generar transacciones entre ellas con montos aleatorios; firmar y enviar por POST al nodo; repetir en intervalo para simular tráfico continuo.

---

## Resumen por componente

| Componente        | Funcionalidad principal |
|-------------------|--------------------------|
| **Nodo**          | Mantener blockchain y mempool; validar y propagar tx/bloques; minar con ProcessPoolExecutor; verificación de cadena con queue.Queue y worker threads; exponer TCP (nodos) y HTTP (billetera); persistir en SQLite; argparse. |
| **Billetera**     | Cliente HTTP; consola para consultas y envío de tx; modo generador de tx de prueba (usuarios y tx aleatorios). |
| **Usuario**       | Entidad lógica (PKI); firmar transacciones; en pruebas, instanciado por el generador. |
| **Gen. génesis**  | Generar semilla y bloque génesis común para todos los nodos. |
| **Gen. tx prueba**| Generar usuarios y transacciones aleatorias; enviar al nodo por HTTP (billetera en modo generador o script). |
