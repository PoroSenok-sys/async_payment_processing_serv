import asyncio
import random

from src.models.enums import PaymentStatus
from src.models.payment import Payment


class EmulatedGateway:
    """Эмулирует платёжный шлюз с задержкой 2–5 секунд и вероятностями результата 90/10."""

    async def charge(self, payment: Payment) -> PaymentStatus:
        """Эмулирует завершённый платёж, включая обычный отказ шлюза."""
        await asyncio.sleep(random.uniform(2, 5))
        return PaymentStatus.SUCCEEDED if random.random() < 0.9 else PaymentStatus.FAILED
