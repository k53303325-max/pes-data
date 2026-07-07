from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Lead, Payment, PaymentStatus, User, UserStatus
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_platform_stats(session: AsyncSession) -> dict:
    total_users = await session.scalar(select(func.count(User.id)))
    active_users = await session.scalar(
        select(func.count(User.id)).where(User.status == UserStatus.ACTIVE.value)
    )
    total_leads = await session.scalar(select(func.count(Lead.id)))
    total_payments = await session.scalar(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.SUCCEEDED.value)
    )
    revenue = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.SUCCEEDED.value
        )
    )

    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "total_leads": total_leads or 0,
        "total_payments": total_payments or 0,
        "revenue": revenue or 0,
    }


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())
