from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    Order,
    OrderStatus,
    Payment,
    Project,
    User,
    UserStatus,
)
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
    from services.referral_service import referral_code_for_user

    user.referral_code = referral_code_for_user(user.id)
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
            selectinload(User.competitor_numbers),
            selectinload(User.deliveries),
            selectinload(User.projects)
            .selectinload(Project.order)
            .selectinload(Order.tariff),
        )
    )
    return result.scalar_one_or_none()


async def refresh_user_status(session: AsyncSession, user_id: int) -> None:
    user = await session.get(User, user_id)
    if not user:
        return
    active = await get_active_order(session, user_id)
    if active:
        user.status = UserStatus.ACTIVE.value
    else:
        has_orders = await session.execute(
            select(Order.id).where(Order.user_id == user_id).limit(1)
        )
        user.status = (
            UserStatus.FINISHED.value
            if has_orders.scalar_one_or_none()
            else UserStatus.NEW.value
        )


def order_remaining(order: Order) -> int:
    return max(0, order.contact_limit - order.received)


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    user = await session.get(User, user_id)
    if not user:
        return False

    try:
        cleanup_sql = [
            """
            DELETE FROM delivered_contacts
            WHERE order_id IN (SELECT id FROM orders WHERE user_id = :uid)
            """,
            """
            DELETE FROM delivered_contacts
            WHERE delivery_id IN (SELECT id FROM deliveries WHERE user_id = :uid)
            """,
            """
            DELETE FROM delivered_contacts
            WHERE delivery_id IN (SELECT id FROM contact_deliveries WHERE user_id = :uid)
            """,
            "DELETE FROM contact_deliveries WHERE user_id = :uid",
            """
            DELETE FROM client_activity_log
            WHERE user_id = :uid
               OR project_id IN (SELECT id FROM projects WHERE user_id = :uid)
            """,
            "DELETE FROM deliveries WHERE user_id = :uid",
            "DELETE FROM competitor_numbers WHERE user_id = :uid",
            "DELETE FROM bot_messages WHERE user_id = :uid",
            "DELETE FROM payments WHERE user_id = :uid",
            "DELETE FROM projects WHERE user_id = :uid",
            "DELETE FROM orders WHERE user_id = :uid",
            "DELETE FROM competitors WHERE user_id = :uid",
        ]
        params = {"uid": user_id}
        for sql in cleanup_sql:
            await session.execute(text(sql), params)

        await session.delete(user)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    logger.info("Deleted user id=%s", user_id)
    return True
