from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import CompetitorNumber, CompetitorStatus, Order, OrderStatus, Project
from services.user_service import order_remaining


@dataclass
class ActiveOrderRow:
    order: Order
    competitor_count: int
    project_id: int | None = None


async def list_active_orders(session: AsyncSession) -> list[ActiveOrderRow]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.tariff))
        .where(
            Order.status.in_(
                [OrderStatus.ACTIVE.value, OrderStatus.IN_PROGRESS.value]
            )
        )
        .order_by(Order.created_at.desc())
    )
    orders = list(result.scalars().all())
    if not orders:
        return []

    user_ids = [o.user_id for o in orders]
    counts_result = await session.execute(
        select(CompetitorNumber.user_id, func.count(CompetitorNumber.id))
        .where(
            CompetitorNumber.user_id.in_(user_ids),
            CompetitorNumber.status == CompetitorStatus.ACTIVE.value,
        )
        .group_by(CompetitorNumber.user_id)
    )
    counts = dict(counts_result.all())

    order_ids = [o.id for o in orders]
    projects_result = await session.execute(
        select(Project.order_id, Project.id).where(Project.order_id.in_(order_ids))
    )
    project_map = dict(projects_result.all())

    return [
        ActiveOrderRow(
            order=order,
            competitor_count=counts.get(order.user_id, 0),
            project_id=project_map.get(order.id),
        )
        for order in orders
    ]


def format_purchase_date(order: Order) -> str:
    value: datetime | None = order.paid_at or order.created_at
    if not value:
        return "—"
    return value.strftime("%d.%m.%Y")
