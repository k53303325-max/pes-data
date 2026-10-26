from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Delivery


async def list_delivery_history(session: AsyncSession, limit: int = 200) -> list[Delivery]:
    result = await session.execute(
        select(Delivery)
        .options(selectinload(Delivery.user), selectinload(Delivery.order))
        .order_by(Delivery.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def delivery_type_label(delivery_type: str) -> str:
    return "Сообщение" if delivery_type == "message" else "Файл"
