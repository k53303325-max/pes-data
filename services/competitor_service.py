from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ActivityType, CompetitorNumber, CompetitorStatus
from services.activity_service import log_activity
from utils.logger import get_logger

logger = get_logger(__name__)

PHONE_RE = re.compile(r"^7\d{10}$")


@dataclass
class ProcessCompetitorsResult:
    lines_received: int
    added: int
    already_tracked: int
    invalid: int
    total_active: int


def validate_competitor_phone(raw: str) -> str | None:
    phone = raw.strip().replace(" ", "")
    if PHONE_RE.match(phone):
        return phone
    return None


def parse_competitor_lines(text: str) -> tuple[list[str], int, int]:
    """Возвращает (уникальные валидные номера, строк получено, невалидных)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines_received = len(lines)
    invalid = 0
    unique: list[str] = []
    seen: set[str] = set()

    for line in lines:
        phone = validate_competitor_phone(line)
        if not phone:
            invalid += 1
            continue
        if phone in seen:
            continue
        seen.add(phone)
        unique.append(phone)

    return unique, lines_received, invalid


async def save_competitors(
    session: AsyncSession,
    user_id: int,
    text: str,
    *,
    project_id: int | None = None,
    added_by: str = "user",
) -> ProcessCompetitorsResult:
    phones, lines_received, invalid = parse_competitor_lines(text)

    existing = set(
        (
            await session.execute(
                select(CompetitorNumber.phone).where(
                    CompetitorNumber.user_id == user_id,
                    CompetitorNumber.status == CompetitorStatus.ACTIVE.value,
                )
            )
        ).scalars()
    )

    added = 0
    already_tracked = 0

    for phone in phones:
        if phone in existing:
            already_tracked += 1
            continue
        session.add(
            CompetitorNumber(
                user_id=user_id,
                project_id=project_id,
                phone=phone,
                added_by=added_by,
                status=CompetitorStatus.ACTIVE.value,
            )
        )
        existing.add(phone)
        added += 1

    if added:
        if project_id:
            await log_activity(
                session,
                project_id=project_id,
                user_id=user_id,
                action_type=ActivityType.COMPETITORS_ADDED.value,
                description=f"Пользователь добавил: {added} номеров конкурентов",
                contacts_count=added,
            )
        await session.commit()
        logger.info(
            "Competitor numbers saved: user_id=%s added=%s already=%s invalid=%s",
            user_id,
            added,
            already_tracked,
            invalid,
        )

    total_active = await count_active_competitors(session, user_id)

    return ProcessCompetitorsResult(
        lines_received=lines_received,
        added=added,
        already_tracked=already_tracked,
        invalid=invalid,
        total_active=total_active,
    )


async def count_active_competitors(session: AsyncSession, user_id: int) -> int:
    result = await session.scalar(
        select(func.count(CompetitorNumber.id)).where(
            CompetitorNumber.user_id == user_id,
            CompetitorNumber.status == CompetitorStatus.ACTIVE.value,
        )
    )
    return result or 0


async def list_active_competitor_phones(session: AsyncSession, user_id: int) -> list[str]:
    result = await session.execute(
        select(CompetitorNumber.phone)
        .where(
            CompetitorNumber.user_id == user_id,
            CompetitorNumber.status == CompetitorStatus.ACTIVE.value,
        )
        .order_by(CompetitorNumber.created_at.desc())
    )
    return list(result.scalars().all())


def format_process_result(result: ProcessCompetitorsResult) -> str:
    return (
        "✅ <b>Номера успешно обработаны.</b>\n\n"
        f"Получено строк:\n{result.lines_received}\n\n"
        f"Добавлено новых:\n{result.added}\n\n"
        f"Уже отслеживаются:\n{result.already_tracked}\n\n"
        f"Всего номеров на отслеживании:\n{result.total_active}\n\n"
        "Мы начали отслеживание указанных номеров.\n\n"
        "Новые контакты будут поступать автоматически по мере их появления."
    )
