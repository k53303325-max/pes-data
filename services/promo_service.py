from __future__ import annotations

import hashlib
import hmac
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import Order, OrderStatus, Payment, PaymentStatus, User, UserStatus
from services.order_service import activate_order_from_payment
from services.tariff_service import TariffInfo


def verify_test_promo(code: str) -> bool:
    """Проверка тестового промокода (бесплатная активация)."""
    expected = settings.promo_test_code.strip()
    if not expected or not code:
        return False
    normalized = "".join(code.split())
    return hmac.compare_digest(normalized, expected)


async def activate_promo_package(
    session: AsyncSession,
    user: User,
    tariff: TariffInfo,
    *,
    contact_limit: int | None = None,
) -> tuple[User, Order]:
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

    limit = contact_limit or tariff.contact_limit
    if not limit:
        raise ValueError("Укажите количество контактов")

    payment = Payment(
        user_id=user.id,
        tariff_id=tariff.id,
        contact_limit=limit,
        amount=0,
        status=PaymentStatus.PENDING.value,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    payment.external_id = f"promo_{uuid.uuid4().hex[:16]}"
    await session.commit()

    return await activate_order_from_payment(session, payment)


def promo_hash_hint() -> str:
    """Подсказка для админа — первые символы хэша, не сам код."""
    if not settings.promo_test_code:
        return "не настроен"
    digest = hashlib.sha256(settings.promo_test_code.encode()).hexdigest()[:12]
    return f"sha256:{digest}…"
