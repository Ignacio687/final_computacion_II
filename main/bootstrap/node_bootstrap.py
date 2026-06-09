"""Composición del nodo: instanciación e inyección de dependencias.

Orden de construcción (contratos en doc/protocolo.md):

    1. Adaptadores crypto:
        signer = CryptographySigner(config.private_key_path, config.public_key_path)
        verifier = CryptographyVerifier()

    2. Codec del sobre TCP (cifrado + firma):
        shared_key = base64decode(config.shared_key)
        codec = MessageCodec(signer, verifier, shared_key)

    3. Persistencia (mismo db_path):
        blockchain_repository = SQLiteBlockchainRepository(config.db_path)
        transaction_repository = SQLiteTransactionRepository(config.db_path)

    4. Génesis (necesario antes de validar/verificar cadenas):
        genesis_provider = SeedGenesisProvider(
            config.genesis_seed, config.genesis_prefund_accounts, config.genesis_prefund_amount,
        )

    5. Validación y minado:
        proof_of_work = SHA256ProofOfWork()
        transaction_validator = DefaultTransactionValidator(verifier)
        block_validator = DefaultBlockValidator(
            proof_of_work, transaction_validator, config.difficulty, config.mining_reward,
        )
        chain_verifier = DefaultChainVerifier(block_validator, genesis_provider)
        chain_dispatcher = ChainVerificationDispatcher(chain_verifier, workers=1)
        pool = ProcessPoolExecutor(max_workers=config.pow_workers)   # cerrar en el stop

    6. Mensajería (sin keepalive; handshake HELLO al conectar):
        message_sender = TCPMessageSender(
            config.peers, signer, codec, config.node_id, config.tcp_port,
            config.reconnect_delay_seconds,
        )
        message_receiver = TCPMessageReceiver(config.bind_host, config.tcp_port, codec)

    7. Servicios:
        propagation_service = PropagationService(
            blockchain_repository, transaction_repository, transaction_validator,
            block_validator, chain_dispatcher, message_sender,
        )
        mining_service = MiningService(
            blockchain_repository, transaction_repository, proof_of_work, message_sender,
            pool, config.difficulty, config.min_transactions_per_block,
            config.block_interval_seconds, config.mining_reward, config.mining_address,
        )
        wallet_query_service = WalletQueryService(
            transaction_repository, blockchain_repository, message_sender,
            config.node_id, config.difficulty,
        )
        transaction_submit_service = TransactionSubmitService(
            transaction_repository, transaction_validator, message_sender,
        )

    8. Controllers (wiring):
        tcp_handler = TCPMessageHandler(propagation_service)
        message_receiver.set_handler(tcp_handler.handle)
        http_handlers = HTTPHandlers(wallet_query_service, transaction_submit_service)
        http_server = HTTPServer(config.bind_host, config.http_port, http_handlers)

    9. Orquestador:
        node_service = NodeService(
            message_sender, message_receiver, blockchain_repository,
            genesis_provider, http_server, propagation_service, mining_service,
            chain_dispatcher,
        )
        await node_service.start()

Nota: PropagationService recibe el `chain_dispatcher` (no el chain_verifier directo) para
encolar la verificación pesada en worker threads.
"""

from main.config.node_config import NodeConfig


async def create_and_run_node(config: NodeConfig) -> None:
    """Crea todas las dependencias siguiendo el orden documentado y ejecuta el nodo
    hasta que se detenga (señal o stop)."""
    raise NotImplementedError
