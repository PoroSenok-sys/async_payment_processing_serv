from contextlib import asynccontextmanager

from src.core.config import settings
from src.core.logging import setup_logging
from src.database import engine


@asynccontextmanager
async def lifespan():
    """Общий жизненный цикл ресурсов процессов API и обработчика сообщений."""
    setup_logging(
        service_name=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        log_level_rules=settings.LOG_LEVEL_RULES,
    )
    try:
        yield
    finally:
        await engine.dispose()
