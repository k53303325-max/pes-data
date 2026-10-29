from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import Order, Payment, ReferralCommission, User
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PartnerCabinetStats:
    invited: int
    paying_clients: int
    total_commission: int
    pending_commission: int
    eligible_commission: int
    paid_out_commission: int


def _commission_amount(paid_amount: int) -> int:
    return paid_amount * settings.referral_commission_percent // 100


async def refresh_eligible_commissions(session: AsyncSession, partner_user_id: int | None = None) -> None:
    now = datetime.now(timezone.utc)
    stmt = select(ReferralCommission).where(
        ReferralCommission.status == "pending",
        ReferralCommission.eligible_at <= now,
    )
    if partner_user_id:
        stmt = stmt.where(ReferralCommission.partner_user_id == partner_user_id)
    rows = (await session.execute(stmt)).scalars().all()
    for row in rows:
        row.status = "eligible"
    if rows:
        await session.commit()


async def create_commission_for_payment(
    session: AsyncSession,
    payment: Payment,
    order: Order,
) -> ReferralCommission | None:
    if payment.amount <= 0:
        return None

    existing = await session.scalar(
        select(ReferralCommission).where(ReferralCommission.payment_id == payment.id)
    )
    if existing:
        return existing

    referee = await session.get(User, payment.user_id)
    if not referee or not referee.referred_by_user_id:
        return None
    if referee.referred_by_user_id == referee.id:
        return None

    partner = await session.get(User, referee.referred_by_user_id)
    if not partner:
        return None

    amount = _commission_amount(payment.amount)
    if amount <= 0:
        return None

    paid_at = payment.paid_at or datetime.now(timezone.utc)
    if paid_at.tzinfo is None:
        paid_at = paid_at.replace(tzinfo=timezone.utc)

    row = ReferralCommission(
        partner_user_id=partner.id,
        referee_user_id=referee.id,
        payment_id=payment.id,
        order_id=order.id,
        paid_amount=payment.amount,
        commission_amount=amount,
        status="pending",
        paid_at=paid_at,
        eligible_at=paid_at + timedelta(days=settings.referral_payout_hold_days),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    logger.info(
        "Referral commission payment_id=%s partner=%s amount=%s",
        payment.id,
        partner.id,
        amount,
    )

    from services.admin_notify_service import notify_admin_referral_commission
    from services.telegram_notify import _telegram_post

    await notify_admin_referral_commission(partner, referee, row)
    await _telegram_post(
        "sendMessage",
        json={
            "chat_id": partner.telegram_id,
            "text": (
                f"🐾 <b>Начислено {amount:,} ₽</b> (10% от оплаты {payment.amount:,} ₽).\n\n"
                f"Выплата — раз в месяц, не раньше чем через "
                f"{settings.referral_payout_hold_days} дней после оплаты клиента. "
                "Статус смотрите в «Кабинет партнёра»."
            ).replace(",", " "),
            "parse_mode": "HTML",
        },
    )
    return row


async def reverse_commission_for_payment(session: AsyncSession, payment_id: int) -> None:
    row = await session.scalar(
        select(ReferralCommission).where(ReferralCommission.payment_id == payment_id)
    )
    if not row or row.status == "reversed":
        return
    if row.status == "paid_out":
        row.status = "review"
        row.admin_note = (row.admin_note or "") + "\n[авто] возврат после выплаты — сверка"
    else:
        row.status = "reversed"
    await session.commit()


async def get_partner_cabinet_stats(session: AsyncSession, partner_user_id: int) -> PartnerCabinetStats:
    await refresh_eligible_commissions(session, partner_user_id)

    invited = int(
        await session.scalar(
            select(func.count(User.id)).where(User.referred_by_user_id == partner_user_id)
        )
        or 0
    )

    paying = int(
        await session.scalar(
            select(func.count(func.distinct(ReferralCommission.referee_user_id))).where(
                ReferralCommission.partner_user_id == partner_user_id,
                ReferralCommission.status != "reversed",
            )
        )
        or 0
    )

    pending = int(
        await session.scalar(
            select(func.coalesce(func.sum(ReferralCommission.commission_amount), 0)).where(
                ReferralCommission.partner_user_id == partner_user_id,
                ReferralCommission.status == "pending",
            )
        )
        or 0
    )
    eligible = int(
        await session.scalar(
            select(func.coalesce(func.sum(ReferralCommission.commission_amount), 0)).where(
                ReferralCommission.partner_user_id == partner_user_id,
                ReferralCommission.status == "eligible",
            )
        )
        or 0
    )
    paid_out = int(
        await session.scalar(
            select(func.coalesce(func.sum(ReferralCommission.commission_amount), 0)).where(
                ReferralCommission.partner_user_id == partner_user_id,
                ReferralCommission.status == "paid_out",
            )
        )
        or 0
    )
    total = pending + eligible + paid_out

    return PartnerCabinetStats(
        invited=invited,
        paying_clients=paying,
        total_commission=total,
        pending_commission=pending,
        eligible_commission=eligible,
        paid_out_commission=paid_out,
    )


async def list_partner_commissions(
    session: AsyncSession, partner_user_id: int, *, limit: int = 20
) -> list[ReferralCommission]:
    result = await session.execute(
        select(ReferralCommission)
        .where(ReferralCommission.partner_user_id == partner_user_id)
        .order_by(ReferralCommission.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
