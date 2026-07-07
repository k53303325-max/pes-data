from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import Order, OrderStatus, Payment, PaymentStatus, Tariff, User, UserStatus
from services.tariff_service import TariffInfo, get_tariff
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PaymentLink:
    payment_db_id: int
    external_id: str
    confirmation_url: str
    amount: int


def _yookassa_configured() -> bool:
    return bool(settings.yookassa_shop_id and settings.yookassa_secret_key)


def _configure_yookassa() -> None:
    from yookassa import Configuration

    Configuration.account_id = settings.yookassa_shop_id
    Configuration.secret_key = settings.yookassa_secret_key


async def create_payment(
    session: AsyncSession,
    user: User,
    tariff: TariffInfo,
    bot_username: str = "Pesdata_bot",
    amount: int | None = None,
) -> PaymentLink:
    if user.status == UserStatus.BLOCKED.value:
        raise ValueError("Аккаунт заблокирован")

    active = await session.execute(
        select(Order.id).where(
            Order.user_id == user.id,
            Order.status.in_([OrderStatus.ACTIVE.value, OrderStatus.IN_PROGRESS.value]),
        ).limit(1)
    )
    if active.scalar_one_or_none():
        raise ValueError("Сначала завершите текущий пакет")

    pay_amount = amount if amount is not None else tariff.price

    payment = Payment(
        user_id=user.id,
        tariff_id=tariff.id,
        amount=pay_amount,
        status=PaymentStatus.PENDING.value,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    if not _yookassa_configured():
        mock_id = f"mock_{uuid.uuid4().hex[:16]}"
        payment.external_id = mock_id
        await session.commit()
        logger.warning("YooKassa not configured — mock payment id=%s", payment.id)
        return PaymentLink(
            payment_db_id=payment.id,
            external_id=mock_id,
            confirmation_url=f"https://t.me/{bot_username}?start=pay_{payment.id}",
            amount=pay_amount,
        )

    _configure_yookassa()
    from yookassa import Payment as YooPayment

    promo_note = " (промокод)" if pay_amount != tariff.price else ""
    payload = {
        "amount": {"value": f"{pay_amount:.2f}", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": settings.yookassa_return_url,
        },
        "capture": True,
        "description": f"Пёс Дата — {tariff.name}{promo_note} ({tariff.contact_limit} контактов)",
        "metadata": {
            "payment_db_id": str(payment.id),
            "user_telegram_id": str(user.telegram_id),
            "tariff_id": str(tariff.id),
        },
    }

    yoo_payment = await asyncio.to_thread(
        YooPayment.create, payload, str(uuid.uuid4())
    )

    payment.external_id = yoo_payment.id
    await session.commit()

    logger.info(
        "YooKassa payment created: external_id=%s user=%s tariff=%s",
        yoo_payment.id,
        user.telegram_id,
        tariff.id,
    )

    return PaymentLink(
        payment_db_id=payment.id,
        external_id=yoo_payment.id,
        confirmation_url=yoo_payment.confirmation.confirmation_url,
        amount=pay_amount,
    )


async def process_successful_payment(
    session: AsyncSession, external_id: str
) -> tuple[User, Order] | None:
    result = await session.execute(
        select(Payment).where(Payment.external_id == external_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        logger.error("Payment not found: external_id=%s", external_id)
        return None

    if payment.status == PaymentStatus.PAID.value:
        user = await session.get(User, payment.user_id)
        order = await session.get(Order, payment.order_id) if payment.order_id else None
        if user and order:
            return user, order
        return None

    tariff_row = await session.get(Tariff, payment.tariff_id)
    if not tariff_row:
        logger.error("Tariff not found for payment id=%s", payment.id)
        return None

    user = await session.get(User, payment.user_id)
    if not user:
        logger.error("User not found for payment id=%s", payment.id)
        return None

    now = datetime.now(timezone.utc)
    order = Order(
        user_id=user.id,
        tariff_id=tariff_row.id,
        contact_limit=tariff_row.contact_limit,
        status=OrderStatus.ACTIVE.value,
        paid_at=now,
    )
    session.add(order)
    await session.flush()

    payment.status = PaymentStatus.PAID.value
    payment.paid_at = now
    payment.order_id = order.id
    user.status = UserStatus.ACTIVE.value

    await session.commit()
    await session.refresh(user)
    await session.refresh(order, ["tariff"])

    logger.info(
        "Payment succeeded: external_id=%s user=%s order=%s",
        external_id,
        user.telegram_id,
        order.id,
    )
    return user, order


async def confirm_mock_payment(session: AsyncSession, payment_db_id: int) -> tuple[User, Order] | None:
    payment = await session.get(Payment, payment_db_id)
    if not payment or not payment.external_id or not payment.external_id.startswith("mock_"):
        return None
    return await process_successful_payment(session, payment.external_id)
