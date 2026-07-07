from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from database.database import async_session, init_db
from database.models import Order, OrderStatus, Payment, PaymentStatus, User, UserStatus


async def seed_demo_active_user(telegram_id: int = 123456789) -> None:
    await init_db()
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Tariff

        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username="demo_user",
                first_name="Иван",
                status=UserStatus.ACTIVE.value,
            )
            session.add(user)
            await session.flush()

        tariff = await session.get(Tariff, 2)
        order = Order(
            user_id=user.id,
            tariff_id=tariff.id,
            contact_limit=tariff.contact_limit,
            received=250,
            status=OrderStatus.ACTIVE.value,
            paid_at=datetime.now(timezone.utc),
        )
        session.add(order)
        await session.flush()

        payment = Payment(
            user_id=user.id,
            order_id=order.id,
            tariff_id=tariff.id,
            amount=tariff.price,
            status=PaymentStatus.PAID.value,
            paid_at=datetime.now(timezone.utc),
        )
        session.add(payment)
        user.status = UserStatus.ACTIVE.value
        await session.commit()
        print(f"Demo user id={user.id} telegram_id={telegram_id} order_id={order.id}")


if __name__ == "__main__":
    asyncio.run(seed_demo_active_user())
