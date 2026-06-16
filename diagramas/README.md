# Diagramas del proyecto HashCoin

Fuentes Mermaid (`.mmd`) alineadas con el código en `main/` (junio 2026).

| Carpeta | Contenido |
|---------|-----------|
| **arquitectura/** | 5 nodos P2P (TCP dual-stack), billetera interactiva + generador Docker, HTTP con fallback. |
| **clase/** | Capas dominio / interfaces / infra / servicios / billetera; `net` dual-stack, `IWalletQuery`, `ActiveAccount`. |
| **entidad/** | SQLite: `blocks`, `transactions`, `mempool`, claves de billetera (archivos PEM, no tabla). |
| **flujo/** | Tx: HTTP → mempool → TCP + allowlist HELLO; bloque: PoW, propagación, GET_CHAIN. |
| **secuencia/** | Propagación de tx y bloque entre nodos; nota de `GET /accounts` en status. |

## Regenerar PNG

Los docs referencian `.png` junto a cada `.mmd`; los PNG no se versionan en el repo. Regenerar con [mermaid-cli](https://github.com/mermaid-js/mermaid-cli):

```bash
npx @mermaid-js/mermaid-cli -i diagramas/arquitectura/arquitectura.mmd -o diagramas/arquitectura/arquitectura.png
# repetir para cada .mmd
```

O con el MCP Mermaid del proyecto en Cursor.

## Última revisión (vs código)

| Tema | Reflejado en diagramas |
|------|------------------------|
| Dual-stack `--bind-host auto` | arquitectura, clase (`DualStackNet`) |
| Allowlist TCP (HELLO + node_id / host) | flujo-transaccion |
| `GET /accounts`, `total_supply` en `/status` | secuencia-transaccion, clase |
| Docker: 5 nodos + wallet generador | arquitectura |
| Tabla `mempool` + `position` en tx | entidad |
