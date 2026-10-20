import asyncio

import httpx

from src.schemas.events import PaymentWebhook


class WebhookSender:
    """Отправляет одну попытку HTTP-уведомления с проверкой статуса и тайм-аутом."""

    def __init__(self, timeout: float = 5) -> None:
        self.timeout = timeout

    async def send(self, url: str, notification: PaymentWebhook) -> None:
        # Ограничиваем весь запрос, а не только ожидание очередной части ответа.
        async with asyncio.timeout(self.timeout):
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=False, trust_env=False
            ) as client:
                # Достаточно статуса ответа; произвольное тело не загружаем в память.
                async with client.stream(
                    "POST", url, json=notification.model_dump(mode="json")
                ) as response:
                    response.raise_for_status()
