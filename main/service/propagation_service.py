"""Servicio de propagación: maneja mensajes entrantes y reenvía cuando corresponde."""

from main.application.interfaces.blockchain_repository import IBlockchainRepository
from main.application.interfaces.transaction_repository import ITransactionRepository
from main.application.interfaces.transaction_validator import ITransactionValidator
from main.application.interfaces.block_validator import IBlockValidator
from main.application.interfaces.chain_verifier import IChainVerifier
from main.application.interfaces.message_sender import IMessageSender
from main.domain.models.message import Message
from main.domain.models.node_info import NodeInfo


class PropagationService:
    """Despacha cada mensaje entrante por tipo y aplica la lógica correspondiente.

    Comportamiento por tipo de mensaje:

    - NEW_TX: validar tx (ITransactionValidator); si es válida y no estaba en
      mempool/cadena, añadir al mempool y broadcast NEW_TX a peers (excepto el origen).
    - NEW_BLOCK: validar bloque (IBlockValidator) contra el último de la cadena local.
      Si es válido, append_block, remove_from_mempool de las tx incluidas, y broadcast
      NEW_BLOCK (excepto al origen). Si el bloque referencia un last_hash que no está
      en la cadena local pero la altura recibida es mayor, enviar GET_CHAIN al origen.
    - GET_CHAIN: responder al origen con CHAIN_RESPONSE conteniendo los bloques desde
      `since_height` (inclusive).
    - CHAIN_RESPONSE: si la cadena recibida es más larga que la local, encolar tarea de
      verificación (IChainVerifier en worker thread). Si la verificación es exitosa,
      replace_chain y reconciliar mempool.
    - GET_MEMPOOL: responder al origen con MEMPOOL_RESPONSE.
    - MEMPOOL_RESPONSE: añadir transacciones nuevas al mempool tras validarlas.
    - PING: responder PONG con el mismo timestamp.
    - PONG: actualizar marca de keepalive del peer.
    """

    def __init__(
        self,
        blockchain_repository: IBlockchainRepository,
        transaction_repository: ITransactionRepository,
        transaction_validator: ITransactionValidator,
        block_validator: IBlockValidator,
        chain_verifier: IChainVerifier,
        message_sender: IMessageSender,
    ) -> None:
        self._blockchain_repository = blockchain_repository
        self._transaction_repository = transaction_repository
        self._transaction_validator = transaction_validator
        self._block_validator = block_validator
        self._chain_verifier = chain_verifier
        self._message_sender = message_sender

    async def handle_message(self, peer: NodeInfo, message: Message) -> None:
        """Punto de entrada único; despacha por message.type y delega en métodos privados."""
        raise NotImplementedError
