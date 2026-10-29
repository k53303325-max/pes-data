from __future__ import annotations

import html
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.database import async_session
from database.models import AdminNotification, User
from services.tariff_service import format_contact_limit, format_price
from services.telegram_notify import _telegram_post
from utils.logger import get_logger

logger = get_logger(__name__)


class NotifyType(str, Enum):
    NEW_REGISTRATION = "new_registration"
    NEW_PROJECT = "new_project"
    PAYMENT = "payment"
    COMPETITOR_ADDED = "competitor_added"
    PACKAGE_COMPLETED = "package_completed"
    ERROR = "error"
    BRIEF = "new_project"


def _fmt_date(value: datetime | None) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.strftime("%d.%m.%Y %H:%M")


def _fmt_date_short(value: datetime | None) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%d.%m.%Y")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.strftime("%d.%m.%Y")


def _user_name(user: User | None) -> str:
    if not user:
        return "—"
    return html.escape(user.first_name or "—")


def _username(user: User | None) -> str:
    if not user or not user.username:
        return "—"
    return f"@{html.escape(user.username)}"


def _is_enabled(cfg: AdminNotification, notify_type: NotifyType) -> bool:
    mapping = {
        NotifyType.NEW_REGISTRATION: cfg.new_registration_enabled,
        NotifyType.NEW_PROJECT: cfg.new_project_enabled,
        NotifyType.PAYMENT: cfg.payment_enabled,
        NotifyType.COMPETITOR_ADDED: cfg.competitor_added_enabled,
        NotifyType.PACKAGE_COMPLETED: cfg.package_completed_enabled,
        NotifyType.ERROR: cfg.error_enabled,
    }
    return mapping.get(notify_type, True)


async def get_notification_configs(session: AsyncSession) -> list[AdminNotification]:
    result = await session.execute(
        select(AdminNotification).order_by(AdminNotification.id)
    )
    return list(result.scalars().all())


async def resolve_admin_telegram_id(session: AsyncSession) -> int | None:
    if settings.admin_telegram_id:
        return settings.admin_telegram_id
    if not settings.admin_username:
        return None
    result = await session.execute(
        select(User.telegram_id).where(
            func.lower(User.username) == settings.admin_username.lower()
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_default_config(session: AsyncSession) -> AdminNotification | None:
    configs = await get_notification_configs(session)
    if configs:
        return configs[0]
    telegram_id = await resolve_admin_telegram_id(session)
    if not telegram_id:
        return None
    cfg = AdminNotification(telegram_id=telegram_id)
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return cfg


async def update_notification_config(
    session: AsyncSession,
    cfg_id: int,
    *,
    telegram_id: int,
    new_registration_enabled: bool,
    new_project_enabled: bool,
    payment_enabled: bool,
    competitor_added_enabled: bool,
    package_completed_enabled: bool,
    error_enabled: bool,
) -> AdminNotification:
    cfg = await session.get(AdminNotification, cfg_id)
    if not cfg:
        raise ValueError("Настройки не найдены")
    cfg.telegram_id = telegram_id
    cfg.new_registration_enabled = new_registration_enabled
    cfg.new_project_enabled = new_project_enabled
    cfg.payment_enabled = payment_enabled
    cfg.competitor_added_enabled = competitor_added_enabled
    cfg.package_completed_enabled = package_completed_enabled
    cfg.error_enabled = error_enabled
    await session.commit()
    await session.refresh(cfg)
    return cfg


async def _send_to_admins(text: str, notify_type: NotifyType) -> None:
    if not settings.bot_token:
        return

    async with async_session() as session:
        configs = await get_notification_configs(session)
        if not configs:
            cfg = await get_or_create_default_config(session)
            configs = [cfg] if cfg else []

        targets = [
            c.telegram_id
            for c in configs
            if c.telegram_id and _is_enabled(c, notify_type)
        ]

    if not targets:
        return

    for chat_id in targets:
        ok, err = await _telegram_post(
            "sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        )
        if not ok:
            logger.warning("Admin notify failed chat_id=%s: %s", chat_id, err[:200])


async def notify_admin_new_registration(user: User) -> None:
    text = (
        "🐶 <b>Новый пользователь!</b>\n\n"
        "Зарегистрирован новый клиент.\n\n"
        f"Имя:\n{_user_name(user)}\n\n"
        f"Username:\n{_username(user)}\n\n"
        f"Telegram ID:\n{user.telegram_id}\n\n"
        f"Дата регистрации:\n{_fmt_date(user.created_at)}"
    )
    await _send_to_admins(text, NotifyType.NEW_REGISTRATION)


async def notify_admin_new_project(user: User, project_name: str) -> None:
    text = (
        "🏢 <b>Новый проект!</b>\n\n"
        "Создан новый проект клиента.\n\n"
        f"Название:\n{html.escape(project_name)}\n\n"
        f"Клиент:\n{_user_name(user)}\n\n"
        f"Username:\n{_username(user)}\n\n"
        f"Дата создания:\n{_fmt_date_short(datetime.now(timezone.utc))}"
    )
    await _send_to_admins(text, NotifyType.NEW_PROJECT)


async def notify_admin_payment(
    user: User,
    *,
    project_name: str | None,
    tariff_name: str,
    price: int,
    contact_limit: int,
    paid_at: datetime | None = None,
) -> None:
    pname = html.escape(project_name) if project_name else "— ожидает названия —"
    text = (
        "💰 <b>Новая оплата!</b>\n\n"
        f"Клиент:\n{_user_name(user)}\n\n"
        f"Проект:\n{pname}\n\n"
        f"Пакет:\n{html.escape(tariff_name)}\n\n"
        f"Сумма:\n{format_price(price)}\n\n"
        f"Лимит:\n{format_contact_limit(contact_limit)} контактов\n\n"
        f"Дата оплаты:\n{_fmt_date(paid_at)}"
    )
    await _send_to_admins(text, NotifyType.PAYMENT)


async def notify_admin_competitors_added(
    user: User,
    *,
    project_name: str | None,
    added: int,
    total: int,
) -> None:
    pname = html.escape(project_name) if project_name else "—"
    text = (
        "📱 <b>Добавлены номера конкурентов</b>\n\n"
        f"Проект:\n{pname}\n\n"
        f"Клиент:\n{_user_name(user)}\n\n"
        f"Добавлено новых номеров:\n{added}\n\n"
        f"Всего номеров на отслеживании:\n{total}\n\n"
        f"Дата:\n{_fmt_date_short(datetime.now(timezone.utc))}"
    )
    await _send_to_admins(text, NotifyType.COMPETITOR_ADDED)


async def notify_admin_package_completed(
    user: User,
    *,
    project_name: str | None,
    tariff_name: str,
    contact_limit: int,
    completed_at: datetime | None = None,
) -> None:
    limit = format_contact_limit(contact_limit)
    pname = html.escape(project_name) if project_name else "—"
    text = (
        "🎉 <b>Пакет завершен!</b>\n\n"
        f"Проект:\n{pname}\n\n"
        f"Клиент:\n{_user_name(user)}\n\n"
        f"Пакет:\n{html.escape(tariff_name)}\n\n"
        f"Получено:\n{limit}/{limit}\n\n"
        f"Дата завершения:\n{_fmt_date(completed_at)}"
    )
    await _send_to_admins(text, NotifyType.PACKAGE_COMPLETED)


def _brief_competitors_line(brief) -> str:
    if brief.competitors_need_help:
        return "нужна помощь с выбором"
    if brief.competitor_phones_raw:
        return html.escape(brief.competitor_phones_raw[:800])
    return "—"


async def notify_admin_brief(user: User, brief) -> bool:
    from services.brief_service import SALES_LABELS

    inn_line = "не запрашивался"
    if brief.is_trial:
        if brief.inn_manual_review:
            inn_line = html.escape(brief.inn_manual_details or "ручная проверка")
        elif brief.inn:
            inn_line = html.escape(brief.inn)

    sales = SALES_LABELS.get(brief.sales_team or "", brief.sales_team or "—")
    pkg = html.escape(brief.package_code or "—")
    source = html.escape(brief.source or "unknown")

    text = (
        f"📋 <b>Новое обращение из бота — {html.escape(brief.request_code)}</b>\n\n"
        f"Дата:\n{_fmt_date(brief.submitted_at or brief.created_at)}\n\n"
        f"Пользователь:\n{_user_name(user)}\n\n"
        f"Username:\n{_username(user)}\n\n"
        f"Telegram ID:\n{user.telegram_id}\n\n"
        f"Бизнес:\n{html.escape((brief.business_text or '—')[:500])}\n\n"
        f"ИНН для триала:\n{inn_line}\n\n"
        f"Обработка:\n{html.escape(sales)}\n\n"
        f"Телефоны конкурентов:\n{_brief_competitors_line(brief)}\n\n"
        f"Пакет (код):\n{pkg}\n\n"
        f"Триал:\n{'да' if brief.is_trial else 'нет'}\n\n"
        f"Источник:\n{source}\n\n"
        f"Статус:\nновое"
    )
    try:
        await _send_to_admins(text, NotifyType.NEW_PROJECT)
        return True
    except Exception:
        logger.exception("notify_admin_brief failed")
        return False


async def notify_admin_trial_interest(user: User, request_code: str) -> None:
    text = (
        "🎁 <b>Запрос на триал (бриф уже был)</b>\n\n"
        f"Обращение:\n{html.escape(request_code)}\n\n"
        f"Клиент:\n{_user_name(user)}\n\n"
        f"Username:\n{_username(user)}\n\n"
        f"Telegram ID:\n{user.telegram_id}"
    )
    await _send_to_admins(text, NotifyType.NEW_PROJECT)


async def notify_admin_referral_event(
    referrer: User,
    referee: User,
    *,
    event: str,
) -> None:
    labels = {
        "registration": "новая регистрация по ссылке",
        "brief": "отправлен бриф",
        "payment": "оплачен пакет",
    }
    label = labels.get(event, event)
    text = (
        f"🤝 <b>Реферал — {html.escape(label)}</b>\n\n"
        f"Пригласивший:\n{_user_name(referrer)}\n\n"
        f"Username:\n{_username(referrer)}\n\n"
        f"ID:\n{referrer.telegram_id}\n\n"
        f"Приглашённый:\n{_user_name(referee)}\n\n"
        f"Username:\n{_username(referee)}\n\n"
        f"ID:\n{referee.telegram_id}\n\n"
        f"Дата:\n{_fmt_date(datetime.now(timezone.utc))}"
    )
    await _send_to_admins(text, NotifyType.NEW_REGISTRATION)


async def notify_admin_bank_payment(user: User, request, pkg) -> None:
    amount = f"{request.amount:,} ₽".replace(",", " ")
    text = (
        "🏦 <b>Оплата с р/с</b>\n\n"
        f"Заявка:\n#{request.id}\n\n"
        f"Пакет:\n{html.escape(pkg.name)}\n\n"
        f"Контактов:\n{request.contact_limit}\n\n"
        f"Сумма:\n{amount}\n\n"
        f"Клиент:\n{_user_name(user)}\n\n"
        f"Username:\n{_username(user)}\n\n"
        f"Telegram ID:\n{user.telegram_id}\n\n"
        f"Дата:\n{_fmt_date(request.created_at)}"
    )
    await _send_to_admins(text, NotifyType.PAYMENT)


async def notify_admin_package_interest(user: User, request_code: str, package_name: str) -> None:
    text = (
        "💬 <b>Интерес к пакету</b>\n\n"
        f"Пакет:\n{html.escape(package_name)}\n\n"
        f"Обращение:\n{html.escape(request_code)}\n\n"
        f"Клиент:\n{_user_name(user)}\n\n"
        f"Username:\n{_username(user)}\n\n"
        f"Telegram ID:\n{user.telegram_id}"
    )
    await _send_to_admins(text, NotifyType.NEW_PROJECT)


async def notify_admin_error(
    *,
    event: str,
    user_label: str,
    error_message: str,
) -> None:
    text = (
        "⚠️ <b>Ошибка системы</b>\n\n"
        f"Событие:\n{html.escape(event)}\n\n"
        f"Пользователь:\n{html.escape(user_label)}\n\n"
        f"Описание:\n{html.escape(error_message[:500])}\n\n"
        f"Дата:\n{_fmt_date(datetime.now(timezone.utc))}"
    )
    await _send_to_admins(text, NotifyType.ERROR)


async def build_daily_report_text(session: AsyncSession) -> str:
    from services.admin_stats_service import dashboard_stats

    stats = await dashboard_stats(session)
    revenue = format_price(int(stats["total_revenue"]))
    return (
        "🐶 <b>Отчет за день</b>\n\n"
        f"Новые регистрации:\n{stats['new_today']}\n\n"
        f"Активных пакетов:\n{stats['active_packages']}\n\n"
        f"Оплаченных заказов:\n{stats['paid_orders']}\n\n"
        f"Выручка:\n{revenue}\n\n"
        f"Отправлено контактов:\n{stats['total_contacts']}\n\n"
        f"Активных клиентов:\n{stats['active_packages']}"
    )


async def notify_admin_daily_report() -> None:
    async with async_session() as session:
        text = await build_daily_report_text(session)
    await _send_to_admins(text, NotifyType.PAYMENT)
