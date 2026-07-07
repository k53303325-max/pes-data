from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from yookassa import Configuration, Payment as YooPayment

from config.settings import settings
from db.models import Payment, PaymentStatus, User, UserStatus
from services.tariff_service import TariffInfo, get_tariff
from utils.logger import get_logger

logger = get_logger(__name__)

Configuration.account_id = settings.yookassa_shop_id
Configuration.secret_key = settings.yookassa_secret_key


@dataclass
class PaymentLink:
    payment_db_id: int
    yookassa_id: str
    confirmation_url: str
    amount: int


def _yookassa_configured() -> bool:
    return bool(settings.yookassa_shop_id and settings.yookassa_secret_key)


async def create_payment(
    session: AsyncSession, user: User, tariff: TariffInfo, bot_username: str = "your_bot"
) -> PaymentLink:
    payment = Payment(
        user_id=user.id,
        amount=tariff.price,
        tariff_id=tariff.id,
        status=PaymentStatus.PENDING.value,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    if not _yookassa_configured():
        mock_id = f"mock_{uuid.uuid4().hex[:16]}"
        payment.payment_id = mock_id
        await session.commit()
        logger.warning(
            "YooKassa not configured — mock payment created: id=%s", mock_id
        )
        return PaymentLink(
            payment_db_id=payment.id,
            yookassa_id=mock_id,
            confirmation_url=f"https://t.me/{bot_username}?start=pay_{payment.id}",
            amount=tariff.price,
        )

    idempotence_key = str(uuid.uuid4())
    yoo_payment = YooPayment.create(
        {
            "amount": {"value": f"{tariff.price:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": settings.yookassa_return_url,
            },
            "capture": True,
            "description": f"Пёс Дата — пакет «{tariff.name}» ({tariff.limit} контактов)",
            "metadata": {
                "payment_db_id": str(payment.id),
                "user_id": str(user.user_id),
                "tariff_id": str(tariff.id),
            },
        },
        idempotence_key,
    )

    payment.payment_id = yoo_payment.id
    await session.commit()

    logger.info(
        "YooKassa payment created: yookassa_id=%s user_id=%s tariff_id=%s",
        yoo_payment.id,
        user.user_id,
        tariff.id,
    )

    return PaymentLink(
        payment_db_id=payment.id,
        yookassa_id=yoo_payment.id,
        confirmation_url=yoo_payment.confirmation.confirmation_url,
        amount=tariff.price,
    )


async def process_successful_payment(
    session: AsyncSession, yookassa_payment_id: str
) -> User | None:
    result = await session.execute(
        select(Payment).where(Payment.payment_id == yookassa_payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        logger.error("Payment not found: yookassa_id=%s", yookassa_payment_id)
        return None

    if payment.status == PaymentStatus.SUCCEEDED.value:
        logger.info("Payment already processed: id=%s", payment.id)
        user = await session.get(User, payment.user_id)
        return user

    tariff = await get_tariff(session, payment.tariff_id)
    if not tariff:
        logger.error("Tariff not found for payment id=%s", payment.id)
        return None

    payment.status = PaymentStatus.SUCCEEDED.value
    user = await session.get(User, payment.user_id)
    if not user:
        logger.error("User not found for payment id=%s", payment.id)
        return None

    user.status = UserStatus.ACTIVE.value
    user.limit = tariff.limit
    user.used = 0
    await session.commit()
    await session.refresh(user)

    logger.info(
        "Payment succeeded: yookassa_id=%s user_id=%s limit=%s",
        yookassa_payment_id,
        user.user_id,
        tariff.limit,
    )
    return user


async def confirm_mock_payment(session: AsyncSession, payment_db_id: int) -> User | None:
    """Dev helper when YooKassa keys are not set."""
    payment = await session.get(Payment, payment_db_id)
    if not payment or not payment.payment_id or not payment.payment_id.startswith("mock_"):
        return None
    return await process_successful_payment(session, payment.payment_id)
