"""Повторная доставка в Telegram контактов, уже сохранённых в deliveries (без изменения заказа)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import DeliveredContact, Delivery, Order, User
from services.telegram_notify import queue_contacts_delivery
from services.user_service import order_remaining


async def requeue_delivery_telegram(session: AsyncSession, delivery_id: int) -> bool:
    delivery = await session.get(
        Delivery,
        delivery_id,
        options=[selectinload(Delivery.user)],
    )
    if not delivery:
        return False
    order = await session.get(Order, delivery.order_id)
    if not order:
        return False
    user = await session.get(User, delivery.user_id)
    if not user:
        return False

    phones = list(
        (
            await session.execute(
                select(DeliveredContact.phone).where(
                    DeliveredContact.delivery_id == delivery.id
                )
            )
        ).scalars()
    )
    if not phones:
        return False

    await queue_contacts_delivery(
        session,
        user,
        phones=phones,
        received=order.received,
        limit=order.contact_limit,
        remaining=order_remaining(order),
        delivery_type=delivery.delivery_type,
        file_name=delivery.file_name,
        file_data=delivery.file_data,
        order_completed=False,
    )
    return True
