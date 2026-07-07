import csv
import io
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from config.settings import settings
from db.database import async_session
from db.models import User
from services.lead_service import count_leads, get_all_leads
from services.stats_service import get_all_users, get_platform_stats
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id


@router.message(Command("admin_users"))
async def admin_users(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    async with async_session() as session:
        users = await get_all_users(session)

    if not users:
        await message.answer("Пользователей нет.")
        return

    lines = ["👥 <b>Пользователи</b>\n"]
    for u in users[:50]:
        lines.append(
            f"• ID {u.user_id} @{u.username or '—'} | {u.status} | "
            f"{u.used}/{u.limit}"
        )

    if len(users) > 50:
        lines.append(f"\n... и ещё {len(users) - 50}")

    await message.answer("\n".join(lines))
    logger.info("Admin viewed users: admin_id=%s", message.from_user.id)


@router.message(Command("admin_leads"))
async def admin_leads(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    async with async_session() as session:
        leads = await get_all_leads(session)

    if not leads:
        await message.answer("Лидов нет.")
        return

    lines = ["📱 <b>Последние лиды</b>\n"]
    for lead in leads[:30]:
        lines.append(f"• {lead.phone} (user_db_id={lead.user_id})")

    if len(leads) > 30:
        lines.append(f"\n... всего {len(leads)}")

    await message.answer("\n".join(lines))
    logger.info("Admin viewed leads: admin_id=%s", message.from_user.id)


@router.message(Command("admin_stats"))
async def admin_stats(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    async with async_session() as session:
        stats = await get_platform_stats(session)

    text = (
        "📊 <b>Статистика платформы</b>\n\n"
        f"Пользователей: {stats['total_users']}\n"
        f"Активных: {stats['active_users']}\n"
        f"Лидов: {stats['total_leads']}\n"
        f"Оплат: {stats['total_payments']}\n"
        f"Выручка: {stats['revenue']:,} ₽".replace(",", " ")
    )
    await message.answer(text)
    logger.info("Admin viewed stats: admin_id=%s", message.from_user.id)


@router.message(Command("admin_export_csv"))
async def admin_export_csv(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    async with async_session() as session:
        leads = await get_all_leads(session)
        users = await get_all_users(session)

    user_map: dict[int, User] = {u.id: u for u in users}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["lead_id", "phone", "telegram_user_id", "username", "created_at"])

    for lead in leads:
        owner = user_map.get(lead.user_id)
        writer.writerow([
            lead.id,
            lead.phone,
            owner.user_id if owner else "",
            owner.username if owner else "",
            lead.created_at.isoformat() if lead.created_at else "",
        ])

    content = output.getvalue().encode("utf-8-sig")
    filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    await message.answer_document(
        BufferedInputFile(content, filename=filename),
        caption=f"Экспорт: {len(leads)} лидов",
    )
    logger.info("Admin exported CSV: admin_id=%s leads=%s", message.from_user.id, len(leads))
