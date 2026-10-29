from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.database import async_session
from database.models import Order, User, UserStatus
from keyboards.start_keyboard import (
    CB_BACK,
    active_user_keyboard,
    finished_user_keyboard,
    welcome_keyboard,
)
from services.messages import (
    BLOCKED_TEXT,
    BOT_SYSTEM_ERROR_TEXT,
    WELCOME_TEXT,
)
from services.order_service import payment_success_text
from services.user_service import (
    get_active_order,
    get_user_by_telegram_id,
    order_remaining,
    register_user,
    touch_user,
)
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


def _active_package_text(first_name: str | None, order: Order) -> str:
    name = first_name or "друг"
    return (
        f"🐶 <b>С возвращением в Пёс Дата</b>, {name}!\n\n"
        f"<b>Ваш пакет:</b>\n{order.tariff.name}\n\n"
        f"<b>Получено:</b>\n{order.received} / {order.contact_limit} контактов\n\n"
        f"<b>Осталось:</b>\n{order_remaining(order)}"
    )


def _finished_package_text(first_name: str | None, received: int) -> str:
    name = first_name or "друг"
    return (
        f"🐶 <b>Ваш пакет завершён</b>, {name}.\n\n"
        f"Вы получили:\n{received} контактов.\n\n"
        f"Чтобы продолжить получать новые контакты, выберите новый пакет."
    )


async def _get_last_order(session, user_id: int) -> Order | None:
    result = await session.execute(
        select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(1)
    )
    order = result.scalar_one_or_none()
    if order:
        await session.refresh(order, ["tariff"])
    return order


async def _resolve_home(session, user: User) -> tuple[str, object | None]:
    if user.status == UserStatus.BLOCKED.value:
        return BLOCKED_TEXT, None

    active = await get_active_order(session, user.id)
    if active:
        await session.refresh(active, ["tariff"])
        if user.status != UserStatus.ACTIVE.value:
            user.status = UserStatus.ACTIVE.value
            await session.commit()
        return _active_package_text(user.first_name, active), active_user_keyboard()

    if user.status == UserStatus.FINISHED.value:
        last = await _get_last_order(session, user.id)
        received = last.received if last else 0
        return _finished_package_text(user.first_name, received), finished_user_keyboard()

    return WELCOME_TEXT, welcome_keyboard()


async def _show_user_home(target: Message, user: User, *, edit: bool = False) -> None:
    async with async_session() as session:
        db_user = await session.get(User, user.id)
        if not db_user:
            return
        await touch_user(session, db_user)
        text, kb = await _resolve_home(session, db_user)

    if edit:
        await target.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    from services.referral_service import attach_referrer, parse_start_payload

    payload = parse_start_payload(command.args)
    if command.args and command.args.strip().split()[0] == "payment_ok":
        await message.answer(
            "✅ Спасибо! Если оплата прошла — бот пришлёт подтверждение в течение минуты.\n"
            "Если сообщения нет — нажмите /start"
        )
        return
    try:
        async with async_session() as session:
            user, is_new = await register_user(
                session,
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
            )
            if is_new and payload.marketing_source and not user.start_source:
                user.start_source = payload.marketing_source
                await session.commit()
                await session.refresh(user)

            if is_new and payload.referrer_user_id:
                attached = await attach_referrer(session, user, payload.referrer_user_id)
                if attached:
                    from services.referral_service import notify_referral_milestones

                    await notify_referral_milestones(session, user, event="registered")

        if is_new:
            logger.info(
                "First visit: telegram_id=%s source=%s referrer=%s",
                message.from_user.id,
                payload.marketing_source,
                payload.referrer_user_id,
            )
            await message.answer(WELCOME_TEXT, reply_markup=welcome_keyboard())
            try:
                from services.admin_notify_service import notify_admin_new_registration

                await notify_admin_new_registration(user)
            except Exception:
                logger.exception(
                    "Admin notify failed for new user telegram_id=%s",
                    message.from_user.id,
                )
            return

        logger.info("Return visit: telegram_id=%s status=%s", user.telegram_id, user.status)
        async with async_session() as session:
            from payments.yookassa import sync_user_pending_payments

            activated = await sync_user_pending_payments(session, user.id)
            if activated:
                _, order = activated
                await message.answer(
                    payment_success_text(order.contact_limit)
                )
                user = await get_user_by_telegram_id(session, message.from_user.id)
        await _show_user_home(message, user)
    except Exception as exc:
        logger.exception("Error in /start telegram_id=%s", message.from_user.id)
        from services.admin_notify_service import notify_admin_error

        await notify_admin_error(
            event="/start",
            user_label=str(message.from_user.id),
            error_message=str(exc),
        )
        await message.answer(BOT_SYSTEM_ERROR_TEXT)


@router.callback_query(F.data == CB_BACK)
async def cb_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            from handlers.menu import show_main_menu_message

            await show_main_menu_message(callback.message, edit=True)
        else:
            from payments.yookassa import sync_user_pending_payments

            activated = await sync_user_pending_payments(session, user.id)
            if activated:
                _, order = activated
                await callback.message.answer(
                    payment_success_text(order.contact_limit)
                )
                user = await get_user_by_telegram_id(session, callback.from_user.id)
            await _show_user_home(callback.message, user, edit=True)
    await callback.answer()
