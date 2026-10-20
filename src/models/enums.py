from enum import StrEnum


class Currency(StrEnum):
    """Поддерживаемые валюты платежа."""

    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatus(StrEnum):
    """Начальный и допустимые финальные статусы платежа."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
