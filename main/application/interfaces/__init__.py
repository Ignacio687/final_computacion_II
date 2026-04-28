# Interfaces (contratos / "puertos" en arquitectura hexagonal).
# Una interfaz por archivo (ISP). Los servicios dependen solo de estas interfaces (DIP).

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.chain_verifier import IChainVerifier
from main.application.interfaces.message_sender import IMessageSender
from main.application.interfaces.message_receiver import IMessageReceiver, MessageHandler
from main.application.interfaces.proof_of_work import IProofOfWork, MiningResult
from main.application.interfaces.signer import ISigner
from main.application.interfaces.verifier import IVerifier
from main.application.interfaces.wallet_query import IWalletQuery
from main.application.interfaces.transaction_submit import ITransactionSubmit
from main.application.interfaces.genesis_provider import IGenesisProvider

__all__ = [
    "IBlockchainRepository",
    "ITransactionRepository",
    "ITransactionValidator",
    "IBlockValidator",
    "IChainVerifier",
    "IMessageSender",
    "IMessageReceiver",
    "MessageHandler",
    "IProofOfWork",
    "MiningResult",
    "ISigner",
    "IVerifier",
    "IWalletQuery",
    "ITransactionSubmit",
    "IGenesisProvider",
]
