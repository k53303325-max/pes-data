from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Competitor
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AddCompetitorsResult:
    saved: int
    duplicates: int


async def add_competitors(
    session: AsyncSession, user_id: int, phones: list[str]
) -> AddCompetitorsResult:
    result = AddCompetitorsResult(saved=0, duplicates=0)

    for phone in phones:
        existing = await session.execute(
            select(Competitor.id).where(
                Competitor.user_id == user_id,
                Competitor.phone == phone,
            )
        )
        if existing.scalar_one_or_none():
            result.duplicates += 1
            continue

        session.add(Competitor(user_id=user_id, phone=phone))
        result.saved += 1

    if result.saved:
        await session.commit()
        logger.info(
            "Competitors added: user_id=%s saved=%s duplicates=%s",
            user_id,
            result.saved,
            result.duplicates,
        )

    return result


async def count_competitors(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(Competitor.id).where(Competitor.user_id == user_id)
    )
    return len(result.scalars().all())
