"""Adaptador: validación de transacciones (firma + reglas)."""

from main.application.interfaces.transaction_validator import ITransactionValidator
from main.application.interfaces.verifier import IVerifier
from main.domain.models.transaction import Transaction


class DefaultTransactionValidator(ITransactionValidator):
    """Implementación de ITransactionValidator; usa IVerifier para la firma."""

    def __init__(self, verifier: IVerifier) -> None:
        self._verifier = verifier

    def validate(self, tx: Transaction) -> bool:
        raise NotImplementedError
