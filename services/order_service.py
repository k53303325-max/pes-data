from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Order, OrderStatus, Payment, PaymentStatus, Tariff, User, UserStatus
from services.project_service import create_project_for_order
from services.pricing_service import order_package_label
from services.tariff_service import format_contact_limit


def payment_success_text(contact_limit: int, *, tariff_name: str | None = None) -> str:
    limit = format_contact_limit(contact_limit)
    package = tariff_name or order_package_label(contact_limit)
    return (
        "✅ <b>Оплата успешно получена!</b>\n\n"
        "Ваш пакет активирован.\n\n"
        f"<b>Пакет:</b>\n{package}\n\n"
        f"<b>Лимит пакета:</b>\n{limit} контактов"
    )


async def activate_order_from_payment(
    session: AsyncSession,
    payment: Payment,
) -> tuple[User, Order]:
    """Создаёт заказ после успешной оплаты и активирует пакет пользователя."""
    if payment.status == PaymentStatus.PAID.value and payment.order_id:
        user = await session.get(User, payment.user_id)
        order = await session.get(Order, payment.order_id)
        if user and order:
            await session.refresh(order, ["tariff"])
            return user, order

    tariff = await session.get(Tariff, payment.tariff_id)
    if not tariff:
        raise ValueError("Тариф не найден")

    user = await session.get(User, payment.user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    contact_limit = payment.contact_limit or tariff.contact_limit
    if not contact_limit:
        raise ValueError("Не указано количество контактов")

    now = datetime.now(timezone.utc)
    order = Order(
        user_id=user.id,
        tariff_id=tariff.id,
        contact_limit=contact_limit,
        received=0,
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

    await create_project_for_order(
        session,
        user,
        order,
        tariff_name=order_package_label(order.contact_limit),
        contact_limit=order.contact_limit,
        price=payment.amount,
    )

    try:
        from services.referral_commission_service import create_commission_for_payment

        await create_commission_for_payment(session, payment, order)
    except Exception:
        pass

    return user, order


async def create_test_order(session: AsyncSession, user_id: int) -> Order:
    """Тестовый заказ для админки — без оплаты."""
    user = await session.get(User, user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    result = await session.execute(
        select(Tariff)
        .where(Tariff.is_active.is_(True))
        .order_by(Tariff.sort_order)
        .limit(1)
    )
    tariff = result.scalar_one_or_none()
    if not tariff:
        raise ValueError("Нет активных тарифов")

    now = datetime.now(timezone.utc)
    order = Order(
        user_id=user.id,
        tariff_id=tariff.id,
        contact_limit=tariff.contact_limit,
        received=0,
        status=OrderStatus.ACTIVE.value,
        paid_at=now,
    )
    session.add(order)
    user.status = UserStatus.ACTIVE.value
    await session.commit()
    await session.refresh(order, ["tariff"])

    user = await session.get(User, user_id)
    if user:
        await create_project_for_order(
            session,
            user,
            order,
            tariff_name=order.tariff.name,
            contact_limit=order.contact_limit,
            price=0,
        )

    return order
