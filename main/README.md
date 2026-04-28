# Estructura del código (HashCoin)

Arquitectura modular orientada a objetos con principios SOLID. Todo está **declarado** (clases, interfaces, modelos, configuración).

---

## Capas

| Carpeta | Qué contiene | De qué depende |
|---------|--------------|----------------|
| `domain/models/` | **Modelos del dominio**: entidades y objetos de valor del problema (Block, Transaction, Account, WalletAccount, NodeInfo, Message, payloads). Son *dataclasses*. Sin lógica ni dependencias externas. | Nada |
| `application/interfaces/` | **Contratos** (clases abstractas, ABC) que definen lo que necesita el negocio: persistencia, validación, mensajería, PoW, criptografía, génesis, consultas para billetera. | `domain/` |
| `infrastructure/` | **Adaptadores**: implementaciones concretas de las interfaces (TCP, HTTP, SQLite, cryptography, SHA-256 PoW, génesis por semilla). | `application/interfaces/`, `domain/` |
| `service/` | **Lógica de negocio** y orquestación: PropagationService, MiningService, TransactionSubmitService, WalletQueryService, NodeService. Dependen solo de interfaces. | `application/interfaces/`, `domain/` |
| `controller/` | **Capa fina de entrada**: TCPMessageHandler (conecta el receiver con propagation) y HTTPHandlers (parsea request/body y delega en interfaces). Sin lógica de negocio. | `service/`, `application/interfaces/` |
| `repository/dto/` | **DTOs** de serialización: BlockDTO, TransactionDTO. Se usan en mensajes TCP (JSON) y en la fila de SQLite. Mantienen un formato estable e independiente del modelo de dominio. | Nada |
| `config/` | **Configuración** parseada con argparse: NodeConfig y WalletConfig. | `domain/` |
| `bootstrap/` | **Composición**: instancia adaptadores y servicios e inyecta dependencias para arrancar el nodo o la billetera. Es el único lugar que conoce las clases concretas. | Todo |
| `wallet/` | Cliente HTTP de la billetera (`WalletClient`). | `domain/` |

## Principios SOLID aplicados

- **SRP**: cada clase hace una sola cosa. `ITransactionValidator` solo valida; `IBlockchainRepository` solo persiste cadena; `MiningService` solo mina; `HTTPHandlers` solo traduce HTTP a llamadas de servicio.
- **OCP**: añadir un nuevo tipo de almacenamiento o transporte = nueva implementación de la interfaz, sin tocar servicios.
- **LSP**: cualquier implementación de una interfaz debe respetar los criterios documentados en sus docstrings.
- **ISP**: interfaces pequeñas y específicas (no hay un único `INode` enorme).
- **DIP**: servicios y controladores dependen de `application/interfaces/*`, no de `infrastructure/*`. La composición ocurre en `bootstrap/`.

---

## Reparto del trabajo (un agente por bloque)

Cada bloque puede implementarse en paralelo sin tocar el resto. **No se cambian firmas de métodos ni nombres de archivos.**

| Bloque | Carpeta | Implementa |
|--------|---------|-----------|
| TCP | `infrastructure/tcp/` | `TCPMessageSender`, `TCPMessageReceiver` |
| HTTP | `infrastructure/http/` | `HTTPServer` |
| SQLite | `infrastructure/persistence/sqlite/` | `SQLiteBlockchainRepository`, `SQLiteTransactionRepository` |
| Crypto | `infrastructure/crypto/` | `CryptographySigner`, `CryptographyVerifier` |
| Validación | `infrastructure/validation/` | `DefaultTransactionValidator`, `DefaultBlockValidator`, `DefaultChainVerifier` |
| Minado | `infrastructure/mining/` | `SHA256ProofOfWork` |
| Génesis | `infrastructure/genesis/` | `SeedGenesisProvider` |
| Servicios | `service/` | `PropagationService`, `MiningService`, `WalletQueryService`, `TransactionSubmitService`, `NodeService` |
| Controladores | `controller/` | `TCPMessageHandler`, `HTTPHandlers` |
| Bootstrap | `bootstrap/` | `create_and_run_node`, `run_wallet` |
| Billetera | `wallet/` | `WalletClient`, consola y generador |

Reglas para todos los bloques:

1. **No modificar** firmas de métodos ni docstrings de `application/interfaces/*` ni atributos de `domain/models/*` y `repository/dto/*`.
2. **Solo importar** desde capas inferiores (servicios no importan infrastructure salvo a través de interfaces; bootstrap es la excepción).
3. Donde un comportamiento esté especificado en el docstring (criterios de validez, formato de mensajes, etc.), respetarlo literalmente.
