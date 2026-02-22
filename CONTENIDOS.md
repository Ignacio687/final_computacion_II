# Contenidos de Computación II

Repositorio de scripts y materiales utilizados en la materia **Computación II** de la Universidad de Mendoza. A continuación se listan todos los contenidos vistos durante la cursada, organizados por clase temática.

---

## 1. I/O, argumentos y manejo de archivos (`Ejercicios/Clase_2_Ejercicios.txt`)

Contenidos introductorios de la materia (no hay carpeta de scripts, pero sí ejercicios que documentan los temas).

- **Argumentos de línea de comando**: parseo de argumentos con `getopt` y/o `argparse` (recibir opciones, flags y valores desde la terminal).
- **Manejo de archivos**: apertura, lectura, escritura y cierre de archivos de texto.
- **Flujos estándar y redirección**: `sys.stdin`, `sys.stdout`, `sys.stderr`; redirección de la salida de error a archivo.
- **Salida de bajo nivel**: escritura directa con file descriptors (`os.write()`).
- **`subprocess.Popen`**: ejecución no bloqueante de procesos externos (concurrencia básica).
- **`os.system()`**: ejecución bloqueante de comandos del sistema.

---

## 2. Procesos (`Clase_3/`)

Creación y gestión de procesos en sistemas UNIX/Linux mediante Python.

- **`os.fork()`**: creación de procesos hijo, obtención de PID/PPID (`os.getpid()`, `os.getppid()`).
- **`os.wait()`**: espera de terminación de procesos hijo.
- **`os.exec*()`** (`os.execlp`): reemplazo del binario del proceso actual por otro programa.
- **Combinación fork + exec + wait**: patrón clásico de creación de procesos.
- **Procesos zombie y huérfanos**: demostración de qué ocurre cuando el hijo termina antes que el padre (zombie) o el padre termina antes que el hijo (huérfano).
- **Separación de memoria entre procesos**: cada proceso tiene su propia copia de las variables tras el fork (Copy-on-Write).
- **Fork múltiple**: creación de varios procesos con `os.fork()` encadenados.
- **File descriptors compartidos**: padre e hijo comparten los file descriptors abiertos antes del fork. Uso de `flush()` para escritura en archivos compartidos.
- **Ejecución secuencial vs concurrente**: contraste entre `os.system()` (bloqueante) y `subprocess.Popen` (no bloqueante/concurrente).
- **Flujos estándar**: `sys.stdin`, `sys.stdout`, `sys.stderr` y su redirección programática.
- **Ejemplo en C**: fork y separación de memoria también demostrado en lenguaje C.

---

## 3. Pipes - Comunicación entre procesos (`Clase_4/`, `Clase_5/`)

Mecanismo IPC (Inter-Process Communication) mediante tuberías.

### Pipes anónimos (`Clase_4/`)
- **`os.pipe()`**: creación de pipes (file descriptors de lectura y escritura).
- **Comunicación padre-hijo**: el padre escribe en el pipe y el hijo lee, transformando los datos (ej. conversión a mayúsculas).
- **`os.read()` / `os.write()`**: lectura y escritura a bajo nivel sobre file descriptors.

### Pipes con `fdopen` y FIFO (`Clase_5/`)
- **`os.fdopen()`**: conversión de file descriptors a objetos archivo de Python para usar `readline()`, `write()`, etc.
- **Comunicación bidireccional padre-hijo** a través de pipes.
- **Lectura continua desde pipes**: bucle de lectura hasta EOF.
- **FIFO (Named Pipes)**: creación con `os.mkfifo()`, comunicación entre procesos no emparentados a través de archivos especiales en `/tmp`.
- **Múltiples hijos leyendo de un mismo pipe**.

---

## 4. Señales (`Clase_6/`)

Manejo de señales POSIX para comunicación asincrónica entre procesos.

- **`signal.signal()`**: registro de handlers personalizados para señales.
- **`signal.getsignal()`**: consultar el manejador actual de una señal.
- **`signal.SIG_IGN`**: ignorar una señal.
- **`signal.SIG_DFL`**: restaurar el comportamiento por defecto de una señal.
- **Señales de usuario**: `SIGUSR1`, `SIGUSR2` con handlers personalizados.
- **`SIGINT`**: interceptar Ctrl+C y personalizar su comportamiento.
- **`SIGTERM`**, **`SIGKILL`**, **`SIGSTOP`**: señales de terminación y detención.
- **`SIGALRM` y `signal.alarm()`**: programar alarmas temporales; `alarm(0)` para deshabilitar.
- **`signal.pause()`**: suspender la ejecución hasta recibir una señal.
- **`os.kill()`**: envío de señales entre procesos (padre a hijo, y viceversa).
- **Frames de señales**: inspección del stack frame al recibir una señal con `traceback.print_stack()`.
- **Ciclo de estados de señales**: ignorar → default → handler personalizado.

---

## 5. Memoria compartida - mmap (`Clase_7/`)

Mapeo de memoria para comunicación entre procesos y acceso eficiente a archivos.

- **`mmap.mmap()` sobre archivo**: mapeo de un archivo a memoria para lectura/escritura directa sin I/O explícito.
- **Memoria anónima compartida**: `mmap.mmap(-1, size)` con `MAP_ANONYMOUS | MAP_SHARED` para compartir regiones de memoria entre procesos sin archivo de respaldo.
- **Comunicación padre-hijo vía mmap**: el hijo escribe en la región mapeada y el padre lee.
- **Sincronización mmap + señales**: uso combinado de mmap para datos y señales (`SIGUSR1`) para sincronización entre procesos.
- **Offsets y cursores**: manejo de `tell()` y `seek()` en regiones mapeadas; el offset no se comparte entre procesos.

---

## 6. Módulo `multiprocessing` (`Clase_8/`)

Abstracción de alto nivel para la creación y gestión de procesos en Python.

- **`multiprocessing.Process`**: creación de procesos con `target`, `start()`, `join()`, `is_alive()`, `kill()`, `terminate()`.
- **`multiprocessing.Lock`**: exclusión mutua entre procesos para proteger secciones críticas.
- **`multiprocessing.Pipe`**: comunicación bidireccional entre procesos con `send()` y `recv()`.
- **`multiprocessing.Queue`**: cola compartida entre procesos (FIFO), `put()` y `get()`.
- **Información de procesos**: `current_process()`, `parent_process()`, `pid`, `ident`.

---

## 7. Pool de procesos y memoria compartida (`Clase_9/`)

Ejecución paralela con pool de workers y variables compartidas.

- **`multiprocessing.Pool`**: pool de procesos reutilizables.
  - `Pool.map()`: aplicar función a múltiples argumentos en paralelo.
  - `Pool.apply()`: aplicar función con un argumento.
  - `Pool.map_async()` / `Pool.apply_async()`: versiones asincrónicas (no bloqueantes).
  - `Pool.starmap()`: map con múltiples argumentos por llamada.
- **`multiprocessing.Value`**: variable compartida entre procesos con tipos C (`'d'` para double, `'i'` para int).
- **`multiprocessing.Array`**: array compartido entre procesos.
- **`Value.acquire()` / `Value.release()`**: bloqueo implícito sobre variables compartidas.

---

## 8. Threads (Hilos) (`Clase_10/`)

Programación concurrente con hilos dentro de un mismo proceso.

- **`threading.Thread`**: creación de hilos con `target`, `start()`, `join()`.
- **Hilos daemon vs no-daemon**: comportamiento al finalizar el hilo principal.
- **`threading.get_ident()` / `threading.get_native_id()`**: identificación de hilos.
- **`threading.current_thread()`**: acceso al hilo actual.
- **`threading.enumerate()`**: listado de hilos activos.
- **Hilos vs procesos**: los hilos comparten PID y espacio de memoria.
- **`queue.Queue`**: cola thread-safe (FIFO) para comunicación entre hilos. También `queue.LifoQueue`.
- **Patrón productor-consumidor** con hilos y colas.

---

## 9. Sincronización de Threads (`Clase_11/`)

Mecanismos para coordinar el acceso a recursos compartidos entre hilos.

- **`threading.Lock`**: bloqueo mutex; `acquire()` y `release()`. Protocolo de contexto (`with`).
- **`threading.Semaphore`**: semáforo contador para limitar el acceso concurrente a un recurso; métodos `acquire()` y `release()` (P/V); protocolo de contexto (`with`).
- **`threading.Barrier`**: punto de sincronización donde todos los hilos deben llegar antes de continuar.
- **`threading.Condition`**: variable de condición para esperar/notificar entre hilos (`wait()`, `notify()`, `notify_all()`).
- **`threading.Event`**: mecanismo de señalización entre hilos (`set()`, `wait()`, `clear()`).
- **`threading.Timer`**: ejecución diferida de una función en un hilo.

---

## 10. Análisis de ejecución y exclusión mutua (`Clase_12/`)

Estudio de race conditions a nivel de instrucciones de máquina.

- **Lenguaje de máquina**: instrucciones como bytes en memoria, opcode, arquitectura del procesador (80x86).
- **Lenguaje ensamblador (x86)**: mnemónicos, una instrucción por línea, relación con código de máquina; ensamblador como programa que traduce a código de máquina; análisis de cómo las instrucciones de alto nivel se traducen a múltiples instrucciones de máquina (load, operate, store), y por qué las operaciones sobre variables compartidas no son atómicas.
- **Race conditions**: demostración de condiciones de carrera con hilos que incrementan y decrementan una variable global.
- **Sección crítica**: concepto y necesidad de proteger regiones de código que acceden a datos compartidos.
- **Exclusión mutua con `threading.Lock`**: solución a race conditions.
- **Ejemplo en C con pthreads**: demostración del mismo problema de concurrencia en C con `pthread_create` y `pthread_join`.

---

## 11. Introducción a Redes y Sockets (`Clase_13/`)

Fundamentos de redes y primera implementación de sockets.

- **Redes de computadoras**: concepto, transferencia de datos en paquetes, alcance y topología.
- **LAN y WAN**: redes de área local vs redes de área amplia.
- **Topologías**: estrella, bus, anillo.
- **Modelo OSI**: las 7 capas (Física, Enlace, Red, Transporte, Sesión, Presentación, Aplicación) y descripción de cada una.
- **Modelo TCP/IP**: las 4 capas (Enlace, Internet, Transporte, Aplicación) y su relación con OSI.
- **Relación entre modelos OSI y TCP/IP**: correspondencia de capas.
- **Protocolos**: TCP, UDP, IP, ICMP, HTTP, SMTP, FTP, DNS; capa de enlace (Ethernet, 802.11, DSL).
- **Puertos**: concepto, puertos bien conocidos (<1024), IANA.
- **`socket.socket()`**: creación de sockets TCP (`AF_INET`, `SOCK_STREAM`) e IPv6 (`AF_INET6`).
- **Servidor TCP básico**: `bind()`, `listen()`, `accept()`, `send()`, `close()`.
- **Cliente TCP básico**: `connect()`, `recv()`, `close()`.
- **Herramientas de red**: telnet, netcat, para pruebas manuales de protocolos (HTTP, SMTP).

---

## 12. Sockets avanzados - Pasivos y activos (`Clase_14/`)

Profundización en el ciclo de vida de un socket.

- **Socket pasivo**: socket en estado de escucha (`listen`), esperando conexiones entrantes.
- **Socket activo**: socket que inicia una conexión (`connect`).
- **Llamadas a sistema de sockets**: `socket()`, `bind()`, `listen()`, `accept()`, `connect()`, `send()`, `recv()`, `close()` y su flujo.

---

## 13. Servidor concurrente con fork (`Clase_15/`)

Servidores que atienden múltiples clientes simultáneamente.

- **Servidor con `os.fork()`**: cada conexión es atendida por un proceso hijo.
- **Manejo de `SIGCHLD`**: `signal.signal(signal.SIGCHLD, signal.SIG_IGN)` para evitar procesos zombie en el servidor.
- **Liberación de recursos**: cierre correcto de sockets en padre e hijo.
- **Modelo cliente-servidor**: arquitectura y flujo de comunicación.

---

## 14. Sockets UDP y `socketserver` (`Clase_16/`)

Protocolo UDP y módulo de alto nivel para servidores.

- **Sockets UDP**: `socket.SOCK_DGRAM`, sin conexión, `sendto()`, `recvfrom()`.
- **Módulo `socketserver`**: framework de alto nivel para crear servidores.
  - `socketserver.UDPServer` / `socketserver.TCPServer`.
  - `socketserver.BaseRequestHandler`: clase base con método `handle()`.
- **Mixins**: `ThreadingMixIn`, `ForkingMixIn` para servidores concurrentes.

---

## 15. Servidor HTTP (`Clase_17/`)

Implementación de servidores HTTP en Python.

- **Protocolo HTTP**: request/response, métodos GET y POST, encabezados, códigos de estado (2xx, 3xx, 4xx, 5xx).
- **`http.server.BaseHTTPRequestHandler`**: handler personalizado con `do_GET()` y `do_POST()`.
- **`http.server.SimpleHTTPRequestHandler`**: servidor de archivos estáticos.
- **`http.server.HTTPServer`** y **`http.server.ThreadingHTTPServer`**: servidor HTTP simple y concurrente con hilos.
- **`socketserver.TCPServer`**: base sobre la cual se construye el servidor HTTP.
- **Servir archivos HTML**: páginas estáticas desde el filesystem.

---

## 16. `concurrent.futures` (`Clase_18/`)

Interfaz de alto nivel para ejecución concurrente y paralela.

- **`concurrent.futures.ThreadPoolExecutor`**: pool de hilos para tareas I/O-bound.
- **`concurrent.futures.ProcessPoolExecutor`**: pool de procesos para tareas CPU-bound.
- **`executor.submit()`**: envío de tareas individuales, retorna `Future`.
- **`executor.map()`**: aplicar función a un iterable de forma concurrente.
- **Objetos `Future`**: `result()`, `done()`, `cancel()`, manejo de excepciones.

---

## 17. IPv6 (`Clase_19/`)

Soporte de IPv6 en programación de sockets.

- **Protocolo IPv6**: direccionamiento, formato de direcciones (ej. `::1`).
- **`socket.AF_INET6`**: familia de direcciones para IPv6.
- **`socket.AF_UNSPEC`**: familia no especificada para soporte dual-stack.
- **`socket.getaddrinfo()`**: resolución de direcciones compatible con IPv4 e IPv6.
- **Servidor dual-stack**: servidor que atiende tanto IPv4 como IPv6 usando hilos.
- **`socketserver` con IPv6**: subclasificación de `TCPServer` con `address_family = socket.AF_INET6`.

---

## 18. Asyncio - Programación asincrónica (`Clase_20/`, `Clase_21/`)

Paradigma de programación asincrónica con un solo hilo y event loop (bucle de eventos).

### Generadores e Iteradores (`Clase_20/`, `Clase_21/`)
- **Generadores**: funciones con `yield` que producen valores bajo demanda.
- **Delegación de generadores**: `yield from` para componer generadores.
- **Iterables e iteradores**: protocolo `__iter__()` / `__next__()`, función `iter()`, función `next()`, excepción `StopIteration`.

### Corrutinas y Asyncio (`Clase_20/`, `Clase_21/`)
- **Corrutinas**: funciones `async def` que pueden suspender su ejecución con `await`.
- **Event loop**: bucle de eventos que ejecuta las corrutinas.
- **`asyncio.run()`**: punto de entrada del event loop.
- **`asyncio.sleep()`**: espera asincrónica sin bloquear el event loop.
- **`asyncio.create_task()`**: ejecución concurrente de corrutinas.
- **`asyncio.gather()`**: espera simultánea de múltiples corrutinas.
- **`aiohttp`**: cliente HTTP asincrónico para requests concurrentes.

### Asyncio Streams (`Clase_21/`)
- **`asyncio.start_server()`**: servidor TCP asincrónico con `StreamReader`/`StreamWriter`.
- **`asyncio.open_connection()`**: cliente TCP asincrónico.
- **`reader.read()` / `writer.write()` / `writer.drain()`**: operaciones de I/O asincrónicas sobre streams.

---

## 19. Docker (`Clase_22/`, `Clase_23/`)

Contenerización de aplicaciones.

### Introducción a Docker (`Clase_22/`)
- **Concepto de contenedores** vs máquinas virtuales (arquitectura, rendimiento, tamaño, aislamiento, gestión de recursos).
- **Imagen**: plantilla con aplicación y dependencias; **contenedor**: instancia de una imagen.
- **Docker Hub**: registro de imágenes públicas y privadas.
- **Orquestación y microservicios**: Docker Swarm, Kubernetes; arquitecturas de microservicios; CI/CD.
- **Instalación de Docker** en Ubuntu/derivados.
- **Comandos básicos**: `docker run`, `docker ps`, `docker images`, `docker stop`, `docker rm`, `docker build`.
- **Dockerfile básico**: `FROM`, `COPY`, `ADD`, `CMD`, `RUN`, `WORKDIR`, `EXPOSE`, `LABEL`, `ENV`, `VOLUME`, `USER`, `ENTRYPOINT`.
- **Otras instrucciones Dockerfile**: `HEALTHCHECK`, `ARG`, `ONBUILD`, `STOPSIGNAL`, `SHELL`.
- **Volúmenes**: persistencia de datos con montaje de directorios del host.

### Docker avanzado (`Clase_23/`)
- **Dockerfile avanzado**: `RUN` para instalar paquetes, imágenes base Alpine.
- **`docker commit`**: crear imágenes a partir de contenedores en ejecución.
- **`docker save` / `docker load`**: exportar e importar imágenes a archivo tar.
- **Networking en Docker**: `docker network`, comunicación entre contenedores, `docker inspect`.
- **Redes predefinidas**: bridge, host, none.
- **Creación y gestión de redes**: `docker network create`, `docker network ls`, `docker network rm`.
- **Conexión de contenedores a redes**: `docker run --network`.
- **Exposición de puertos** de contenedores al host.

---

## 20. Ejercicios prácticos (`Ejercicios/`)

Ejercicios correspondientes a cada clase, cubriendo todos los temas anteriores:

- Clase 2: Introducción
- Clase 3: Fork, exec, wait, zombie
- Clase 4: Pipes
- Clase 5: Pipes y FIFO
- Clase 6: Señales
- Clase 7: mmap
- Clase 8: multiprocessing (Process, Lock, Pipe, Queue)
- Clase 9: Pool, memoria compartida
- Clase 10: Threads
- Clase 11: Sincronización de threads
- Clase 12: Exclusión mutua, race conditions
- Clase 14: Sockets
- Clase 15: Servidor con fork
- Clase 16: Sockets UDP, socketserver
- Clase 17: HTTP server
- Clase 18: concurrent.futures
- Clase 19: IPv6
- Clase 21: Asyncio streams
- Clase 22: Docker
- Clase 23: Docker avanzado

---

## 21. Trabajo Práctico (`TPs/`)

### TP2 - Procesamiento de imágenes con servidor HTTP concurrente
Trabajo integrador que combina múltiples contenidos de la materia:
- Servidor HTTP concurrente que recibe imágenes.
- Procesamiento de imágenes (conversión a escala de grises).
- IPC entre el servidor HTTP y un servicio de procesamiento (hijo).
- Mecanismo de sincronización para esperar la finalización del procesamiento.
- Segundo servidor para escalado de imágenes.
- Soporte dual-stack IPv4/IPv6.
- Parseo de argumentos con `getopt`/`argparse`.
- Manejo de errores.

---

## Resumen de contenidos por categoría

| Categoría | Contenidos |
|-----------|-----------|
| **Procesos** | `fork`, `exec`, `wait`, zombie, huérfano, `Popen`, `os.system` |
| **IPC** | Pipes anónimos, FIFO (named pipes), `multiprocessing.Pipe`, `multiprocessing.Queue`, `mmap`, señales |
| **Señales** | `signal.signal`, `signal.getsignal`, `SIG_IGN`, `SIG_DFL`, `SIGUSR1/2`, `SIGINT`, `SIGTERM`, `SIGKILL`, `SIGSTOP`, `SIGALRM`, `SIGCHLD`, `os.kill`, `signal.pause`, `signal.alarm` |
| **Memoria compartida** | `mmap` (archivo y anónimo), `multiprocessing.Value`, `multiprocessing.Array` |
| **Multiprocessing** | `Process`, `Lock`, `Pipe`, `Queue`, `Pool`, `Value`, `Array` |
| **Threads** | `threading.Thread`, `daemon`, `Lock`, `Semaphore`, `Barrier`, `Condition`, `Event`, `Timer`, `queue.Queue` |
| **Sincronización** | Lock, Semaphore, Barrier, Condition, Event, exclusión mutua, sección crítica, race conditions |
| **Sockets** | TCP (`SOCK_STREAM`), UDP (`SOCK_DGRAM`), `AF_INET`, `AF_INET6`, `AF_UNSPEC`, `bind`, `listen`, `accept`, `connect`, `send`, `recv`, `sendto`, `recvfrom` |
| **Servidores** | Servidor TCP/UDP, servidor concurrente con fork, `socketserver`, servidor HTTP, `ThreadingMixIn`, `ForkingMixIn` |
| **HTTP** | Protocolo HTTP, métodos GET/POST, códigos de estado, `http.server`, `BaseHTTPRequestHandler`, `SimpleHTTPRequestHandler` |
| **Alto nivel** | `concurrent.futures` (`ThreadPoolExecutor`, `ProcessPoolExecutor`), `asyncio` |
| **Asyncio** | Generadores, iteradores, corrutinas, `async`/`await`, `create_task`, `gather`, streams (`start_server`, `open_connection`) |
| **IPv6** | Direccionamiento IPv6, dual-stack, `AF_INET6`, `getaddrinfo`, `AF_UNSPEC` |
| **Docker** | Contenedores, Dockerfile, `docker run/build/commit`, volúmenes, networking, imágenes Alpine |
| **Bajo nivel** | Lenguaje de máquina (opcode), lenguaje ensamblador x86, análisis de instrucciones de máquina, file descriptors, llamadas a sistema |
| **Redes (conceptos)** | LAN, WAN, topologías (estrella, bus, anillo), relación OSI–TCP/IP, ICMP, capa de enlace (Ethernet, 802.11) |
| **Docker (extendido)** | Imagen, contenedor, Docker Hub, docker build/save/load, orquestación (Swarm, Kubernetes), microservicios, CI/CD, redes predefinidas (bridge, host, none), instrucciones Dockerfile (LABEL, WORKDIR, EXPOSE, ENV, VOLUME, USER, HEALTHCHECK, ARG, ONBUILD) |
