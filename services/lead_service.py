from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Lead, User
from services.user_service import remaining
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AddLeadsResult:
    saved: int
    duplicates: int
    invalid: int
    skipped_limit: int


async def add_leads(
    session: AsyncSession, user: User, phones: list[str]
) -> AddLeadsResult:
    result = AddLeadsResult(saved=0, duplicates=0, invalid=0, skipped_limit=0)
    slots = remaining(user)

    if slots <= 0:
        result.skipped_limit = len(phones)
        return result

    for phone in phones:
        if result.saved >= slots:
            result.skipped_limit += 1
            continue

        existing = await session.execute(
            select(Lead.id).where(Lead.user_id == user.id, Lead.phone == phone)
        )
        if existing.scalar_one_or_none():
            result.duplicates += 1
            continue

        session.add(Lead(user_id=user.id, phone=phone))
        result.saved += 1

    if result.saved > 0:
        user.used += result.saved
        await session.commit()
        await session.refresh(user)
        logger.info(
            "Leads added: user_id=%s saved=%s used=%s/%s",
            user.user_id,
            result.saved,
            user.used,
            user.limit,
        )

    return result


async def count_leads(session: AsyncSession, user_db_id: int | None = None) -> int:
    query = select(func.count(Lead.id))
    if user_db_id is not None:
        query = query.where(Lead.user_id == user_db_id)
    result = await session.execute(query)
    return result.scalar_one()


async def get_all_leads(session: AsyncSession) -> list[Lead]:
    result = await session.execute(select(Lead).order_by(Lead.created_at.desc()))
    return list(result.scalars().all())


async def get_user_leads(session: AsyncSession, user_db_id: int) -> list[Lead]:
    result = await session.execute(
        select(Lead).where(Lead.user_id == user_db_id).order_by(Lead.created_at.desc())
    )
    return list(result.scalars().all())
