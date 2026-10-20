from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import SessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    """Предоставляет сессию; транзакцией управляет сервис через session.begin()."""
    async with SessionLocal() as session:
        yield session
