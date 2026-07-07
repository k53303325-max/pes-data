from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    ContactDelivery,
    DeliveredContact,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    User,
    UserStatus,
)


async def dashboard_stats(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = await session.scalar(select(func.count(User.id))) or 0
    new_today = await session.scalar(
        select(func.count(User.id)).where(User.created_at >= today_start)
    ) or 0
    active_packages = await session.scalar(
        select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.ACTIVE.value, OrderStatus.IN_PROGRESS.value])
        )
    ) or 0
    completed_packages = await session.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED.value)
    ) or 0
    paid_orders = await session.scalar(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.PAID.value)
    ) or 0
    total_revenue = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.PAID.value
        )
    ) or 0
    total_contacts = await session.scalar(select(func.count(DeliveredContact.id))) or 0

    return {
        "total_users": total_users,
        "new_today": new_today,
        "active_packages": active_packages,
        "completed_packages": completed_packages,
        "paid_orders": paid_orders,
        "total_revenue": total_revenue,
        "total_contacts": total_contacts,
    }


async def list_users(
    session: AsyncSession,
    q: str = "",
    status: str = "",
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        if q.isdigit():
            stmt = stmt.where(User.telegram_id == int(q))
        else:
            stmt = stmt.where(User.username.ilike(f"%{q.lstrip('@')}%"))
    if status:
        stmt = stmt.where(User.status == status)
    result = await session.execute(stmt.options(selectinload(User.orders)))
    return list(result.scalars().all())


async def sales_by_day(session: AsyncSession, days: int = 14) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(
            func.date(Payment.paid_at).label("day"),
            func.count(Payment.id).label("count"),
            func.coalesce(func.sum(Payment.amount), 0).label("sum"),
        )
        .where(Payment.status == PaymentStatus.PAID.value, Payment.paid_at >= since)
        .group_by(func.date(Payment.paid_at))
        .order_by(func.date(Payment.paid_at))
    )
    return [{"day": str(r.day), "count": r.count, "sum": r.sum} for r in result.all()]
