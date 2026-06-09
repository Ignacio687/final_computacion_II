"""Composición del nodo: instanciación e inyección de dependencias."""

import asyncio
import base64
from concurrent.futures import ProcessPoolExecutor

from main.config.node_config import NodeConfig
from main.controller.http_handlers import HTTPHandlers
from main.controller.tcp_handler import TCPMessageHandler
from main.infrastructure.crypto.signer import CryptographySigner
from main.infrastructure.crypto.verifier import CryptographyVerifier
from main.infrastructure.genesis.seed_genesis_provider import SeedGenesisProvider
from main.infrastructure.http.http_server import HTTPServer
from main.infrastructure.mining.proof_of_work import SHA256ProofOfWork
from main.infrastructure.persistence.sqlite.blockchain_repository import (
    SQLiteBlockchainRepository,
)
from main.infrastructure.persistence.sqlite.transaction_repository import (
    SQLiteTransactionRepository,
)
from main.infrastructure.serialization.message_codec import MessageCodec
from main.infrastructure.tcp.tcp_message_receiver import TCPMessageReceiver
from main.infrastructure.tcp.tcp_message_sender import TCPMessageSender
from main.infrastructure.validation.block_validator import DefaultBlockValidator
from main.infrastructure.validation.chain_verification_dispatcher import (
    ChainVerificationDispatcher,
)
from main.infrastructure.validation.chain_verifier import DefaultChainVerifier
from main.infrastructure.validation.transaction_validator import DefaultTransactionValidator
from main.service.mining_service import MiningService
from main.service.node_service import NodeService
from main.service.propagation_service import PropagationService
from main.service.transaction_submit_service import TransactionSubmitService
from main.service.wallet_query_service import WalletQueryService


async def create_and_run_node(config: NodeConfig) -> None:
    """Crea todas las dependencias y ejecuta el nodo hasta detenerse."""
    signer = CryptographySigner(config.private_key_path, config.public_key_path)
    verifier = CryptographyVerifier()
    shared_key = base64.b64decode(config.shared_key)

    codec = MessageCodec(signer, verifier, shared_key)

    blockchain_repository = SQLiteBlockchainRepository(config.db_path)
    transaction_repository = SQLiteTransactionRepository(config.db_path)

    genesis_provider = SeedGenesisProvider(
        config.genesis_seed,
        config.genesis_prefund_accounts,
        config.genesis_prefund_amount,
    )

    proof_of_work = SHA256ProofOfWork()
    transaction_validator = DefaultTransactionValidator(
        verifier, transaction_repository
    )
    block_validator = DefaultBlockValidator(
        proof_of_work,
        transaction_validator,
        config.difficulty,
        config.mining_reward,
    )
    chain_verifier = DefaultChainVerifier(block_validator, genesis_provider)
    chain_dispatcher = ChainVerificationDispatcher(chain_verifier, workers=1)
    pool = ProcessPoolExecutor(max_workers=config.pow_workers)

    message_sender = TCPMessageSender(
        config.peers,
        signer,
        codec,
        config.node_id,
        config.tcp_port,
        config.reconnect_delay_seconds,
    )
    message_receiver = TCPMessageReceiver(
        config.bind_host,
        config.tcp_port,
        codec,
        config.node_id,
        config.tcp_port,
        message_sender,
        signer.get_public_key(),
    )

    propagation_service = PropagationService(
        blockchain_repository,
        transaction_repository,
        transaction_validator,
        block_validator,
        chain_dispatcher,
        message_sender,
    )
    mining_service = MiningService(
        blockchain_repository,
        transaction_repository,
        proof_of_work,
        message_sender,
        pool,
        config.difficulty,
        config.min_transactions_per_block,
        config.block_interval_seconds,
        config.mining_reward,
        config.mining_address,
    )
    wallet_query_service = WalletQueryService(
        transaction_repository,
        blockchain_repository,
        message_sender,
        config.node_id,
        config.difficulty,
    )
    transaction_submit_service = TransactionSubmitService(
        transaction_repository,
        transaction_validator,
        message_sender,
    )

    tcp_handler = TCPMessageHandler(propagation_service)
    message_receiver.set_handler(tcp_handler.handle)
    message_sender.set_handler(tcp_handler.handle)
    http_handlers = HTTPHandlers(wallet_query_service, transaction_submit_service)
    http_server = HTTPServer(config.bind_host, config.http_port, http_handlers)

    node_service = NodeService(
        message_sender,
        message_receiver,
        blockchain_repository,
        genesis_provider,
        http_server,
        propagation_service,
        mining_service,
        chain_dispatcher,
    )

    try:
        await node_service.start()
    except asyncio.CancelledError:
        pass
    finally:
        await node_service.stop()
        pool.shutdown(wait=False)
