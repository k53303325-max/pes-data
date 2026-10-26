from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import ActivityType, ClientActivityLog, Project


async def log_activity(
    session: AsyncSession,
    *,
    project_id: int,
    user_id: int,
    action_type: str,
    description: str,
    contacts_count: int | None = None,
    admin_id: str | None = None,
) -> ClientActivityLog:
    entry = ClientActivityLog(
        project_id=project_id,
        user_id=user_id,
        action_type=action_type,
        description=description,
        contacts_count=contacts_count,
        admin_id=admin_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_recent_activities(session: AsyncSession, limit: int = 15) -> list[ClientActivityLog]:
    result = await session.execute(
        select(ClientActivityLog)
        .options(selectinload(ClientActivityLog.project), selectinload(ClientActivityLog.user))
        .order_by(ClientActivityLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_project_activities(
    session: AsyncSession, project_id: int
) -> list[ClientActivityLog]:
    result = await session.execute(
        select(ClientActivityLog)
        .where(ClientActivityLog.project_id == project_id)
        .order_by(ClientActivityLog.created_at.desc())
    )
    return list(result.scalars().all())


def format_activity_line(entry: ClientActivityLog, project_name: str | None) -> str:
    name = project_name or "Проект"
    if entry.action_type == ActivityType.CONTACTS_SENT.value:
        count = entry.contacts_count or 0
        return f"🏢 {name}\n+{count} контактов отправлено"
    if entry.action_type == ActivityType.COMPETITORS_ADDED.value:
        count = entry.contacts_count or 0
        return f"🏢 {name}\nДобавлено {count} номеров конкурентов"
    if entry.action_type == ActivityType.PAYMENT.value:
        return f"🏢 {name}\n{entry.description}"
    if entry.action_type == ActivityType.PROJECT_CREATED.value:
        return f"🏢 {name}\nПроект создан"
    return f"🏢 {name}\n{entry.description}"
