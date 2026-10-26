from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    BriefRequestStatus,
    NicheBriefRequest,
    TrialEntitlement,
    TrialEntitlementStatus,
    User,
)
from utils.inn import validate_inn
from utils.phone import extract_phones_with_stats

SALES_LABELS = {
    "team": "Есть отдел продаж",
    "self": "Звоню сам",
    "none": "Пока некому звонить",
}

TRIAL_BLOCKING_STATUSES = {
    TrialEntitlementStatus.CHECKING.value,
    TrialEntitlementStatus.RESERVED.value,
    TrialEntitlementStatus.ISSUING.value,
    TrialEntitlementStatus.COMPLETED.value,
}

TRIAL_INN_ACTIVE_STATUSES = {
    TrialEntitlementStatus.REQUESTED.value,
    *TRIAL_BLOCKING_STATUSES,
}


class TrialCheckResult:
    __slots__ = ("ok", "reason")

    def __init__(self, ok: bool, reason: str | None = None) -> None:
        self.ok = ok
        self.reason = reason


async def get_latest_submitted_brief(session: AsyncSession, user_id: int) -> NicheBriefRequest | None:
    result = await session.execute(
        select(NicheBriefRequest)
        .where(
            NicheBriefRequest.user_id == user_id,
            NicheBriefRequest.status == BriefRequestStatus.SUBMITTED.value,
        )
        .order_by(NicheBriefRequest.submitted_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_draft_brief(session: AsyncSession, user_id: int) -> NicheBriefRequest | None:
    result = await session.execute(
        select(NicheBriefRequest)
        .where(
            NicheBriefRequest.user_id == user_id,
            NicheBriefRequest.status.in_(
                [BriefRequestStatus.DRAFT.value, BriefRequestStatus.NOTIFY_FAILED.value]
            ),
        )
        .order_by(NicheBriefRequest.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_or_create_draft(
    session: AsyncSession,
    user: User,
    *,
    is_trial: bool,
    package_code: str | None,
    source: str | None,
) -> NicheBriefRequest:
    draft = await get_draft_brief(session, user.id)
    if draft:
        draft.is_trial = is_trial or draft.is_trial
        if package_code:
            draft.package_code = package_code
        if source and not draft.source:
            draft.source = source
        await session.commit()
        await session.refresh(draft)
        return draft

    brief = NicheBriefRequest(
        user_id=user.id,
        request_code="BR-DRAFT",
        status=BriefRequestStatus.DRAFT.value,
        is_trial=is_trial,
        package_code=package_code,
        source=source or user.start_source,
    )
    session.add(brief)
    await session.flush()
    brief.request_code = f"BR-{brief.id:06d}"
    await session.commit()
    await session.refresh(brief)
    return brief


def parse_competitor_input(text: str) -> tuple[list[str], str | None, bool]:
    """Returns normalized phones, first bad token, need_help flag."""
    phones, invalid = extract_phones_with_stats(text)
    bad: str | None = None
    if invalid:
        for part in text.replace("\n", " ").split():
            part = part.strip(",;")
            if any(ch.isdigit() for ch in part) and len([c for c in part if c.isdigit()]) >= 6:
                from utils.phone import normalize_phone

                if not normalize_phone(part):
                    bad = part[:40]
                    break
    return phones, bad, False


async def check_trial_inn(session: AsyncSession, user: User, inn: str) -> TrialCheckResult:
    result = await session.execute(
        select(TrialEntitlement).where(TrialEntitlement.inn == inn).limit(1)
    )
    row = result.scalar_one_or_none()
    if row:
        if row.status in TRIAL_BLOCKING_STATUSES:
            return TrialCheckResult(False, "inn_used")
        if row.status in TRIAL_INN_ACTIVE_STATUSES:
            if row.telegram_id != user.telegram_id:
                return TrialCheckResult(False, "inn_active")
            if row.status != TrialEntitlementStatus.REQUESTED.value:
                return TrialCheckResult(False, "inn_active")

    other = await session.execute(
        select(TrialEntitlement)
        .where(TrialEntitlement.telegram_id == user.telegram_id)
        .limit(1)
    )
    other_row = other.scalar_one_or_none()
    if other_row and other_row.inn != inn and other_row.status in TRIAL_INN_ACTIVE_STATUSES:
        return TrialCheckResult(False, "telegram_other_inn")

    if other_row and other_row.inn == inn:
        return TrialCheckResult(True, None)

    user_trials = await session.execute(
        select(TrialEntitlement).where(
            TrialEntitlement.user_id == user.id,
            TrialEntitlement.status.in_(tuple(TRIAL_BLOCKING_STATUSES)),
        )
    )
    if user_trials.scalar_one_or_none():
        return TrialCheckResult(False, "telegram_used")

    return TrialCheckResult(True, None)


async def reserve_trial_for_inn(
    session: AsyncSession,
    user: User,
    inn: str,
    brief_id: int,
) -> None:
    result = await session.execute(select(TrialEntitlement).where(TrialEntitlement.inn == inn))
    row = result.scalar_one_or_none()
    if row:
        row.user_id = user.id
        row.telegram_id = user.telegram_id
        row.brief_request_id = brief_id
        if row.status == TrialEntitlementStatus.RELEASED.value:
            row.status = TrialEntitlementStatus.REQUESTED.value
    else:
        session.add(
            TrialEntitlement(
                user_id=user.id,
                telegram_id=user.telegram_id,
                inn=inn,
                status=TrialEntitlementStatus.REQUESTED.value,
                brief_request_id=brief_id,
            )
        )
    await session.commit()


def format_summary(brief: NicheBriefRequest) -> str:
    inn_line = "не запрашивался"
    if brief.is_trial:
        if brief.inn_manual_review:
            inn_line = brief.inn_manual_details or "ручная проверка (без ИНН)"
        elif brief.inn:
            inn_line = brief.inn
        else:
            inn_line = "—"

    sales = SALES_LABELS.get(brief.sales_team or "", brief.sales_team or "—")

    if brief.competitors_need_help:
        phones = "нужна помощь с выбором"
    elif brief.competitor_phones_normalized:
        phones = "\n".join(phones_from_storage(brief.competitor_phones_normalized))
    else:
        phones = brief.competitor_phones_raw or "—"

    return (
        "<b>Проверьте вводные:</b>\n\n"
        f"<b>Бизнес:</b>\n{brief.business_text or '—'}\n\n"
        f"<b>ИНН для триала:</b>\n{inn_line}\n\n"
        f"<b>Обработка контактов:</b>\n{sales}\n\n"
        f"<b>Телефоны конкурентов:</b>\n{phones}"
    )


async def submit_brief(session: AsyncSession, brief: NicheBriefRequest) -> NicheBriefRequest:
    brief.status = BriefRequestStatus.SUBMITTED.value
    brief.submitted_at = datetime.now(timezone.utc)
    if brief.is_trial and brief.inn and not brief.inn_manual_review:
        await reserve_trial_for_inn(session, brief.user, brief.inn, brief.id)
    else:
        await session.commit()
    await session.refresh(brief)
    return brief


def phones_to_storage(phones: list[str]) -> str:
    return json.dumps(phones, ensure_ascii=False)


def phones_from_storage(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data]
    except json.JSONDecodeError:
        pass
    return [p.strip() for p in raw.split(",") if p.strip()]


def validate_inn_field(text: str) -> tuple[bool, str | None]:
    ok, inn = validate_inn(text)
    return ok, inn
