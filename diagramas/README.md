# Diagramas del proyecto HashCoin

Fuentes Mermaid (`.mmd`) alineadas con el código en `main/` (noviembre 2026).

| Carpeta | Contenido |
|---------|-----------|
| **arquitectura/** | 5 nodos P2P (TCP/HTTP con listeners **nativos** IPv4+IPv6 en `auto`), billetera + generador Compose, HTTP con fallback. |
| **clase/** | Capas dominio / interfaces / infra / servicios / billetera; módulo `dual_stack.py` (`DualStackNet`), `IWalletQuery`, `ActiveAccount`. |
| **entidad/** | SQLite: `blocks`, `transactions`, `mempool`, claves de billetera (archivos PEM, no tabla). |
| **flujo/** | Tx: HTTP → mempool → TCP + allowlist HELLO; bloque: PoW, propagación, GET_CHAIN. |
| **secuencia/** | Propagación de tx y bloque entre nodos; nota de `GET /accounts` en status. |

## Regenerar PNG

Los docs referencian `.png` junto a cada `.mmd`. Regenerar con [mermaid-cli](https://github.com/mermaid-js/mermaid-cli):

```bash
npx @mermaid-js/mermaid-cli -i diagramas/arquitectura/arquitectura.mmd -o diagramas/arquitectura/arquitectura.png
# repetir para cada .mmd tocado
```

O con el MCP Mermaid del proyecto en Cursor (`generate_mermaid_diagram`, `outputType=file`).

## Última revisión (vs código)

| Tema | Reflejado en diagramas |
|------|------------------------|
| Listeners **nativos** `--bind-host auto` (sockets dedicados IPv4+IPv6, `IPV6_V6ONLY=1`) | arquitectura, clase (`DualStackNet` / `dual_stack.py`) |
| Allowlist TCP (HELLO + node_id / host) | flujo-transaccion |
| `GET /accounts`, `total_supply` en `/status` | secuencia-transaccion, clase |
| Docker Compose IPv4: 5 nodos + wallet generador (demo IPv6 = local) | arquitectura |
| Tabla `mempool` + `position` en tx | entidad |
