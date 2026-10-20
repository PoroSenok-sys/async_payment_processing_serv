from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.schemas.errors import ErrorResponse
from src.schemas.payment import PaymentAccepted, PaymentCreate, PaymentDetails
from src.services.payment import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])
Database = Annotated[AsyncSession, Depends(get_db)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=255, pattern=r"^\S+$"),
]


@router.post(
    "", status_code=202, response_model=PaymentAccepted,
    summary="Создать платёж",
    responses={409: {"model": ErrorResponse, "description": "Ключ идемпотентности использован с другими данными"}},
)
async def create_payment(data: PaymentCreate, idempotency_key: IdempotencyKey, db: Database):
    """Создаёт платёж и событие outbox либо возвращает платёж с тем же ключом."""
    return await PaymentService(db).create(data, idempotency_key)


@router.get(
    "/{payment_id}", response_model=PaymentDetails,
    summary="Получить платёж",
    responses={404: {"model": ErrorResponse, "description": "Платёж не найден"}},
)
async def get_payment(payment_id: Annotated[int, Path(gt=0, le=2147483647)], db: Database):
    """Возвращает данные и текущее состояние платежа по его идентификатору."""
    return await PaymentService(db).get(payment_id)
