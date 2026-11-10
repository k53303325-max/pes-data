from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Order, OrderStatus, Payment, PaymentStatus
from services.competitor_service import count_active_competitors, list_project_competitor_phones
from services.project_service import list_projects_for_active_order
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
    project_name: str | None
    project_needs_name: bool


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
    order_projects = await list_projects_for_active_order(session, user_id)
    named = [p for p in order_projects if p.project_name]
    project_name = named[0].project_name if named else None
    project_needs_name = any(not p.project_name for p in order_projects)

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
        project_name=project_name,
        project_needs_name=project_needs_name,
    )


def _format_date(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.strftime("%d.%m.%Y")


def _format_project_block(data: ProfileData) -> str:
    if data.project_name:
        name = html.escape(data.project_name)
        return (
            f"🏢 <b>Проект</b>\n\n"
            f"{name}\n\n"
            f"📱 Номеров в проекте: {data.competitors_count}\n\n"
        )
    if data.project_needs_name:
        return (
            "🏢 <b>Проект</b>\n\n"
            "Откройте «Мои проекты» и укажите название — затем можно добавить номера.\n\n"
        )
    return ""


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
        f"{_format_project_block(data)}"
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


def format_project_numbers_block(phones: list[str], total: int) -> str:
    shown = phones[:COMPETITORS_PAGE_SIZE]
    lines = "\n".join(f"<code>{phone}</code>" for phone in shown)
    suffix = ""
    if total > len(shown):
        suffix = "\n\n..."
    if total == 0:
        return (
            "📱 <b>Номера конкурентов</b>\n\n"
            "Пока нет. После создания проекта нажмите «Добавить номера»."
        )
    return (
        "📱 <b>Номера конкурентов</b>\n\n"
        f"Всего номеров:\n{total}\n\n"
        f"{lines}{suffix}"
    )


def format_project_need_name_text() -> str:
    from services.project_service import PROJECT_NAME_PROMPT

    return (
        "🏢 <b>Мои проекты</b>\n\n"
        "Сначала создайте проект — укажите его название в следующем сообщении.\n\n"
        f"{PROJECT_NAME_PROMPT}"
    )


def format_project_detail_text(project_name: str, phones: list[str], total: int) -> str:
    name = html.escape(project_name)
    return (
        "🏢 <b>Мои проекты</b>\n\n"
        f"<b>Название:</b>\n{name}\n\n"
        f"{format_project_numbers_block(phones, total)}"
    )


def format_projects_list_text(projects: list) -> str:
    if not projects:
        return (
            "🏢 <b>Мои проекты</b>\n\n"
            "Проектов пока нет. Нажмите «Создать проект»."
        )
    lines = []
    for p in projects:
        name = html.escape(p.project_name or "— без названия —")
        lines.append(f"• {name}")
    body = "\n".join(lines)
    return (
        "🏢 <b>Мои проекты</b>\n\n"
        f"{body}\n\n"
        "Выберите проект или создайте новый."
    )


async def get_project_detail_view(
    session: AsyncSession, user_id: int, project_id: int
) -> tuple[str, bool, bool]:
    from services.project_service import get_project_for_user

    project = await get_project_for_user(session, user_id, project_id)
    if not project:
        return "Проект не найден.", False, False
    if not project.project_name:
        return format_project_need_name_text(), True, False
    phones = await list_project_competitor_phones(session, project.id)
    total = len(phones)
    return (
        format_project_detail_text(project.project_name, phones, total),
        False,
        True,
    )
