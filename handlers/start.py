from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.database import async_session
from database.models import Order, User, UserStatus
from keyboards.start_keyboard import (
    CB_ADD_COMPETITORS,
    CB_BACK,
    CB_BUY_NEW,
    CB_CHOOSE_PACKAGE,
    CB_FAQ,
    CB_HOW_IT_WORKS,
    CB_MY_PACKAGE,
    active_user_keyboard,
    choose_package_keyboard,
    finished_user_keyboard,
    welcome_keyboard,
)
from services.messages import (
    ADD_COMPETITORS_STUB,
    BLOCKED_TEXT,
    CHOOSE_PACKAGE_STUB,
    FAQ_TEXT,
    HOW_IT_WORKS_TEXT,
    MY_PACKAGE_STUB,
    WELCOME_TEXT,
)
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

    if user.status == UserStatus.NEW.value:
        return WELCOME_TEXT, welcome_keyboard()

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
async def cmd_start(message: Message) -> None:
    try:
        async with async_session() as session:
            user, is_new = await register_user(
                session,
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
            )

        if is_new:
            logger.info("First visit: telegram_id=%s", message.from_user.id)
            await message.answer(WELCOME_TEXT, reply_markup=welcome_keyboard())
            return

        logger.info("Return visit: telegram_id=%s status=%s", user.telegram_id, user.status)
        await _show_user_home(message, user)
    except Exception:
        logger.exception("Error in /start telegram_id=%s", message.from_user.id)
        await message.answer("⚠️ Ошибка. Попробуйте /start ещё раз.")


@router.callback_query(F.data == CB_HOW_IT_WORKS)
async def cb_how_it_works(callback: CallbackQuery) -> None:
    await callback.message.edit_text(HOW_IT_WORKS_TEXT, reply_markup=choose_package_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_FAQ)
async def cb_faq(callback: CallbackQuery) -> None:
    await callback.message.edit_text(FAQ_TEXT, reply_markup=choose_package_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({CB_CHOOSE_PACKAGE, CB_BUY_NEW}))
async def cb_choose_package(callback: CallbackQuery) -> None:
    await callback.message.edit_text(CHOOSE_PACKAGE_STUB, reply_markup=choose_package_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_MY_PACKAGE)
async def cb_my_package(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        active = await get_active_order(session, user.id)
        if active:
            await session.refresh(active, ["tariff"])
            text = _active_package_text(user.first_name, active)
            kb = active_user_keyboard()
        else:
            text = MY_PACKAGE_STUB
            kb = active_user_keyboard()
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == CB_ADD_COMPETITORS)
async def cb_add_competitors(callback: CallbackQuery) -> None:
    await callback.message.edit_text(ADD_COMPETITORS_STUB, reply_markup=active_user_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_BACK)
async def cb_back(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.message.edit_text(WELCOME_TEXT, reply_markup=welcome_keyboard())
    else:
        await _show_user_home(callback.message, user, edit=True)
    await callback.answer()
