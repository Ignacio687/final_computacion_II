# Mejoras y características futuras

<!-- Lista detallada de mejoras y posibles nuevas características del sistema para futuras versiones. -->

## Validaciones de configuración

- Validar al arrancar el nodo que `--mining-address` sea una dirección con formato válido (id de cuenta de usuario bien formado, derivable de una clave pública). Hoy se acepta cualquier string.

## Red y descubrimiento

- Descubrimiento automático de peers (hoy la lista de peers se pasa por `--peers`).

## Persistencia

- Compactación / poda de la base SQLite cuando la cadena crezca mucho.

## Despliegue

- Crear `Dockerfile` (imagen base con Python y dependencias del proyecto, copia del código y `ENTRYPOINT` apuntando a `run.py`).
- Crear `docker-compose.yml` con 4–5 servicios de nodo (cada uno con su `--node-id`, `--tcp-port`, `--http-port`, `--peers`, `--pow-workers` distintos, asignando distinta cantidad de cores con `cpus:` para observar competencia de PoW) y 1 servicio de billetera en modo generador. Todos los nodos comparten el mismo `--genesis-seed` por variable de entorno común.
