# Diagramas del proyecto HashCoin

Diagramas generados con Mermaid (MCP). Cada subcarpeta corresponde a un tipo.

| Carpeta | Contenido |
|---------|-----------|
| **arquitectura/** | Vista de componentes: nodos en red local, billetera cliente, protocolos TCP y HTTP. |
| **clase/** | Diagrama de clases: Nodo, Billetera, Block, Transaction, Usuario y relaciones. |
| **entidad/** | Diagrama entidad-relación: Block, Transaction, Node, Account (blockchain y billetera). |
| **flujo/** | Flujos: creación y propagación de transacción; minado y propagación de bloque. |
| **secuencia/** | Secuencias: billetera → nodo → peers (tx); nodo → ProcessPool → peers (bloque). |

Las fuentes Mermaid (`.mmd`) permiten regenerar los PNG con el MCP o con [mermaid-cli](https://github.com/mermaid-js/mermaid-cli).
