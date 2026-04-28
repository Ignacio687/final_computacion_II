"""Composición del nodo: instanciación e inyección de dependencias.

Orden de construcción:

    1. Adaptadores crypto:
        signer = CryptographySigner(config.private_key_path, config.public_key_path)
        verifier = CryptographyVerifier()

    2. Persistencia (mismo db_path):
        blockchain_repository = SQLiteBlockchainRepository(config.db_path)
        transaction_repository = SQLiteTransactionRepository(config.db_path)

    3. Validación y minado:
        proof_of_work = SHA256ProofOfWork()
        block_validator = DefaultBlockValidator(proof_of_work)
        transaction_validator = DefaultTransactionValidator(verifier)
        chain_verifier = DefaultChainVerifier(block_validator)

    4. Génesis:
        genesis_provider = SeedGenesisProvider(config.genesis_seed)

    5. Mensajería:
        message_sender = TCPMessageSender(
            config.peers, signer,
            config.reconnect_initial_seconds, config.reconnect_max_seconds,
        )
        message_receiver = TCPMessageReceiver(config.bind_host, config.tcp_port, verifier)

    6. Servicios:
        propagation_service = PropagationService(
            blockchain_repository, transaction_repository, transaction_validator,
            block_validator, chain_verifier, message_sender,
        )
        mining_service = MiningService(
            blockchain_repository, transaction_repository, proof_of_work, message_sender,
            config.difficulty, config.min_transactions_per_block,
            config.block_interval_seconds, config.mining_reward, config.mining_address,
        )
        wallet_query_service = WalletQueryService(
            transaction_repository, blockchain_repository,
            config.node_id, config.difficulty, get_peers_connected=lambda: ...,
        )
        transaction_submit_service = TransactionSubmitService(
            transaction_repository, transaction_validator, message_sender,
        )

    7. HTTP:
        http_server = HTTPServer(
            config.bind_host, config.http_port,
            wallet_query_service, transaction_submit_service,
        )

    8. Orquestador:
        node_service = NodeService(
            message_sender, message_receiver, blockchain_repository,
            genesis_provider, http_server, propagation_service, mining_service,
        )
        await node_service.start()
"""

from main.config.node_config import NodeConfig


async def create_and_run_node(config: NodeConfig) -> None:
    """Crea todas las dependencias siguiendo el orden documentado y ejecuta el nodo
    hasta que se detenga (señal o stop)."""
    raise NotImplementedError
