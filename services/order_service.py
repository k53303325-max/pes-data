from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from database.database import TARIFFS
from database.models import Order, OrderStatus, Tariff, User, UserStatus


async def create_test_order(session: AsyncSession, user_id: int) -> Order:
    """Тестовый заказ для админки — без оплаты."""
    user = await session.get(User, user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    tariff_data = TARIFFS[0]
    tariff = await session.get(Tariff, tariff_data["id"])
    if not tariff:
        tariff = Tariff(**tariff_data)
        session.add(tariff)
        await session.flush()

    now = datetime.now(timezone.utc)
    order = Order(
        user_id=user.id,
        tariff_id=tariff.id,
        contact_limit=tariff.contact_limit,
        status=OrderStatus.ACTIVE.value,
        paid_at=now,
    )
    session.add(order)
    user.status = UserStatus.ACTIVE.value
    await session.commit()
    await session.refresh(order, ["tariff"])
    return order
