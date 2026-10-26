from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    BankPaymentRequest,
    NicheBriefRequest,
    TrialEntitlement,
    TrialEntitlementStatus,
    User,
)
from services.brief_service import SALES_LABELS


BRIEF_STATUS_LABELS = {
    "draft": "Черновик",
    "submitted": "Отправлено",
    "notify_failed": "Ошибка отправки",
}

TRIAL_STATUS_LABELS = {
    TrialEntitlementStatus.REQUESTED.value: "Запрошен",
    TrialEntitlementStatus.CHECKING.value: "На проверке",
    TrialEntitlementStatus.RESERVED.value: "Зарезервирован",
    TrialEntitlementStatus.ISSUING.value: "Выдаётся",
    TrialEntitlementStatus.COMPLETED.value: "Завершён",
    TrialEntitlementStatus.RELEASED.value: "Освобождён",
}

BANK_STATUS_LABELS = {
    "new": "Новая",
    "invoiced": "Счёт выставлен",
    "paid": "Оплачено",
    "canceled": "Отменена",
}


async def list_briefs(session: AsyncSession, *, limit: int = 200) -> list[NicheBriefRequest]:
    result = await session.execute(
        select(NicheBriefRequest)
        .options(selectinload(NicheBriefRequest.user))
        .where(NicheBriefRequest.status != "draft")
        .order_by(NicheBriefRequest.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_brief(session: AsyncSession, brief_id: int) -> NicheBriefRequest | None:
    result = await session.execute(
        select(NicheBriefRequest)
        .options(selectinload(NicheBriefRequest.user))
        .where(NicheBriefRequest.id == brief_id)
    )
    return result.scalar_one_or_none()


async def list_trials(session: AsyncSession, *, limit: int = 200) -> list[TrialEntitlement]:
    result = await session.execute(
        select(TrialEntitlement)
        .options(selectinload(TrialEntitlement.user))
        .order_by(TrialEntitlement.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_trial_status(session: AsyncSession, trial_id: int, status: str) -> TrialEntitlement:
    row = await session.get(TrialEntitlement, trial_id)
    if not row:
        raise ValueError("Запись не найдена")
    if status not in TRIAL_STATUS_LABELS:
        raise ValueError("Недопустимый статус")
    row.status = status
    await session.commit()
    await session.refresh(row)
    return row


async def list_bank_payments(session: AsyncSession, *, limit: int = 200) -> list[BankPaymentRequest]:
    result = await session.execute(
        select(BankPaymentRequest)
        .options(selectinload(BankPaymentRequest.user))
        .order_by(BankPaymentRequest.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_bank_payment_status(
    session: AsyncSession,
    request_id: int,
    status: str,
    *,
    admin_note: str | None = None,
) -> BankPaymentRequest:
    row = await session.get(BankPaymentRequest, request_id)
    if not row:
        raise ValueError("Заявка не найдена")
    if status not in BANK_STATUS_LABELS:
        raise ValueError("Недопустимый статус")
    row.status = status
    if admin_note is not None:
        row.admin_note = admin_note.strip() or None
    await session.commit()
    await session.refresh(row)
    return row


def format_sales_team(key: str | None) -> str:
    if not key:
        return "—"
    return SALES_LABELS.get(key, key)
