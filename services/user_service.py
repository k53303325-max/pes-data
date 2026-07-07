from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Order, OrderStatus, Payment, User, UserStatus
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def register_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> tuple[User, bool]:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        user.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(user)
        return user, False

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        status=UserStatus.NEW.value,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info("New user: telegram_id=%s username=%s", telegram_id, username)
    return user, True


async def touch_user(session: AsyncSession, user: User) -> None:
    user.updated_at = datetime.now(timezone.utc)
    await session.commit()


async def get_active_order(session: AsyncSession, user_id: int) -> Order | None:
    result = await session.execute(
        select(Order)
        .where(
            Order.user_id == user_id,
            Order.status.in_([OrderStatus.ACTIVE.value, OrderStatus.IN_PROGRESS.value]),
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_user_with_orders(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.orders).selectinload(Order.tariff),
            selectinload(User.payments).selectinload(Payment.tariff),
            selectinload(User.competitors),
            selectinload(User.deliveries),
        )
    )
    return result.scalar_one_or_none()


def order_remaining(order: Order) -> int:
    return max(0, order.contact_limit - order.received)
