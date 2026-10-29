from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import Order, OrderStatus, Payment, PaymentStatus, User
from utils.logger import get_logger

logger = get_logger(__name__)

REF_PREFIX = "ref"


@dataclass(frozen=True)
class ParsedStartPayload:
    marketing_source: str | None = None
    referrer_user_id: int | None = None


def parse_start_payload(args: str | None) -> ParsedStartPayload:
    if not args:
        return ParsedStartPayload()
    token = args.strip().split()[0][:64]
    if not token or token == "payment_ok":
        return ParsedStartPayload()
    if token.startswith(REF_PREFIX) and len(token) > len(REF_PREFIX):
        tail = token[len(REF_PREFIX) :]
        if tail.isdigit():
            return ParsedStartPayload(referrer_user_id=int(tail), marketing_source=token)
    return ParsedStartPayload(marketing_source=token)


def referral_code_for_user(user_id: int) -> str:
    return f"{REF_PREFIX}{user_id}"


def referral_link_for_user(user_id: int) -> str:
    bot = settings.bot_username or "Pesdata_bot"
    code = referral_code_for_user(user_id)
    return f"https://t.me/{bot.lstrip('@')}?start={code}"


async def ensure_user_referral_code(session: AsyncSession, user: User) -> str:
    code = referral_code_for_user(user.id)
    if user.referral_code != code:
        user.referral_code = code
        await session.commit()
    return code


async def attach_referrer(
    session: AsyncSession,
    user: User,
    referrer_user_id: int,
) -> bool:
    if user.referred_by_user_id:
        return False
    if referrer_user_id == user.id:
        return False
    referrer = await session.get(User, referrer_user_id)
    if not referrer:
        return False
    user.referred_by_user_id = referrer_user_id
    if not user.start_source:
        user.start_source = referral_code_for_user(referrer_user_id)
    await session.commit()
    logger.info(
        "Referral attached: user_id=%s referrer_id=%s",
        user.id,
        referrer_user_id,
    )
    return True


@dataclass
class ReferralStats:
    invited: int
    briefs_submitted: int
    paid: int


async def get_referral_stats(session: AsyncSession, user_id: int) -> ReferralStats:
    invited = await session.scalar(
        select(func.count(User.id)).where(User.referred_by_user_id == user_id)
    )
    invited = int(invited or 0)

    from database.models import BriefRequestStatus, NicheBriefRequest

    briefs_submitted = await session.scalar(
        select(func.count(func.distinct(NicheBriefRequest.user_id)))
        .select_from(NicheBriefRequest)
        .join(User, User.id == NicheBriefRequest.user_id)
        .where(
            User.referred_by_user_id == user_id,
            NicheBriefRequest.status == BriefRequestStatus.SUBMITTED.value,
        )
    )
    briefs_submitted = int(briefs_submitted or 0)

    paid = await session.scalar(
        select(func.count(func.distinct(User.id)))
        .select_from(User)
        .join(Payment, Payment.user_id == User.id)
        .where(
            User.referred_by_user_id == user_id,
            Payment.status == PaymentStatus.PAID.value,
        )
    )
    paid = int(paid or 0)

    return ReferralStats(invited=invited, briefs_submitted=briefs_submitted, paid=paid)


async def get_referrer(session: AsyncSession, user: User) -> User | None:
    if not user.referred_by_user_id:
        return None
    return await session.get(User, user.referred_by_user_id)


async def notify_referral_milestones(session: AsyncSession, referee: User, *, event: str) -> None:
    referrer = await get_referrer(session, referee)
    if not referrer:
        return

    from services.admin_notify_service import notify_admin_referral_event
    from services.telegram_notify import _telegram_post

    if event == "registered":
        await notify_admin_referral_event(referrer, referee, event="registration")
    elif event == "brief_submitted":
        await notify_admin_referral_event(referrer, referee, event="brief")
    elif event == "paid":
        await notify_admin_referral_event(referrer, referee, event="payment")
        text = (
            "🤝 <b>Партнёрская программа</b>\n\n"
            "По вашей ссылке клиент оплатил пакет. "
            "Команда свяжется с вами по условиям бонуса."
        )
        await _telegram_post(
            "sendMessage",
            json={"chat_id": referrer.telegram_id, "text": text, "parse_mode": "HTML"},
        )
