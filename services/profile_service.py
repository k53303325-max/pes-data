from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Order, OrderStatus, Payment, PaymentStatus
from services.competitor_service import count_active_competitors, list_active_competitor_phones
from services.tariff_service import format_contact_limit, format_price
from services.user_service import get_active_order, order_remaining

DIVIDER = "━━━━━━━━━━━━━━"
COMPETITORS_PAGE_SIZE = 20


@dataclass
class ProfileData:
    order: Order
    tariff_name: str
    price: int
    contact_limit: int
    received: int
    remaining: int
    competitors_count: int
    purchase_date: datetime | None
    is_completed: bool


async def _get_order_payment_amount(session: AsyncSession, order: Order) -> int:
    result = await session.execute(
        select(Payment.amount)
        .where(
            Payment.order_id == order.id,
            Payment.status == PaymentStatus.PAID.value,
        )
        .order_by(Payment.paid_at.desc())
        .limit(1)
    )
    amount = result.scalar_one_or_none()
    if amount is not None:
        return amount

    result = await session.execute(
        select(Payment.amount)
        .where(
            Payment.user_id == order.user_id,
            Payment.tariff_id == order.tariff_id,
            Payment.status == PaymentStatus.PAID.value,
        )
        .order_by(Payment.paid_at.desc())
        .limit(1)
    )
    amount = result.scalar_one_or_none()
    if amount is not None:
        return amount

    await session.refresh(order, ["tariff"])
    return order.tariff.price


async def get_last_completed_order(session: AsyncSession, user_id: int) -> Order | None:
    result = await session.execute(
        select(Order)
        .where(
            Order.user_id == user_id,
            Order.status == OrderStatus.COMPLETED.value,
        )
        .order_by(Order.completed_at.desc(), Order.created_at.desc())
        .limit(1)
    )
    order = result.scalar_one_or_none()
    if order:
        await session.refresh(order, ["tariff"])
    return order


async def load_profile_data(session: AsyncSession, user_id: int) -> ProfileData | None:
    order = await get_active_order(session, user_id)
    is_completed = False

    if not order:
        order = await get_last_completed_order(session, user_id)
        if not order:
            return None
        is_completed = True
    else:
        await session.refresh(order, ["tariff"])

    competitors_count = await count_active_competitors(session, user_id)
    price = await _get_order_payment_amount(session, order)
    purchase_date = order.paid_at or order.created_at

    return ProfileData(
        order=order,
        tariff_name=order.tariff.name,
        price=price,
        contact_limit=order.contact_limit,
        received=order.received,
        remaining=order_remaining(order),
        competitors_count=competitors_count,
        purchase_date=purchase_date,
        is_completed=is_completed,
    )


def _format_date(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.strftime("%d.%m.%Y")


def format_cabinet_text(data: ProfileData) -> str:
    limit = format_contact_limit(data.contact_limit)
    return (
        "🐶 <b>Пёс Дата</b>\n\n"
        "Личный кабинет\n\n"
        f"{DIVIDER}\n\n"
        f"📦 <b>Пакет</b>\n\n"
        f"{data.tariff_name}\n\n"
        f"💰 <b>Стоимость</b>\n\n"
        f"{format_price(data.price)}\n\n"
        f"📊 <b>Лимит пакета</b>\n\n"
        f"{limit} контактов\n\n"
        f"📥 <b>Уже получено</b>\n\n"
        f"{format_contact_limit(data.received)} контактов\n\n"
        f"📤 <b>Осталось получить</b>\n\n"
        f"{format_contact_limit(data.remaining)} контактов\n\n"
        f"📱 <b>Номеров конкурентов на отслеживании</b>\n\n"
        f"{data.competitors_count}\n\n"
        f"📅 <b>Дата покупки</b>\n\n"
        f"{_format_date(data.purchase_date)}\n\n"
        f"🟢 <b>Статус</b>\n\n"
        "Активен\n\n"
        f"{DIVIDER}\n\n"
        "Новые контакты будут автоматически приходить в этот чат "
        "после их обработки."
    )


def format_completed_text(data: ProfileData) -> str:
    limit = format_contact_limit(data.contact_limit)
    received = format_contact_limit(data.received)
    return (
        "🎉 <b>Ваш пакет полностью выполнен.</b>\n\n"
        f"Вы получили:\n\n"
        f"{received} контактов из {limit}.\n\n"
        "Спасибо за использование сервиса «Пёс Дата»."
    )


def format_competitors_text(phones: list[str], total: int) -> str:
    shown = phones[:COMPETITORS_PAGE_SIZE]
    lines = "\n".join(f"<code>{phone}</code>" for phone in shown)
    suffix = ""
    if total > len(shown):
        suffix = "\n\n..."
    return (
        "📱 <b>Ваши конкуренты</b>\n\n"
        f"Всего номеров:\n{total}\n\n"
        f"{lines}{suffix}"
    )


async def get_competitors_view(session: AsyncSession, user_id: int) -> tuple[str, int]:
    phones = await list_active_competitor_phones(session, user_id)
    total = len(phones)
    return format_competitors_text(phones, total), total
