from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from keyboards.profile_keyboard import (
    CB_BACK_TO_PROFILE,
    CB_BUY_PACKAGE,
    CB_MY_COMPETITORS,
    CB_MY_PACKAGE,
    CB_PROFILE,
    CB_REFRESH_PROFILE,
    cabinet_keyboard,
    completed_keyboard,
    competitors_keyboard,
    no_package_keyboard,
)
from keyboards.start_keyboard import CB_BUY_NEW
from services.profile_service import (
    format_cabinet_text,
    format_completed_text,
    get_competitors_view,
    load_profile_data,
)
from services.user_service import get_active_order, get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

PROFILE_CALLBACKS = {
    CB_PROFILE,
    CB_MY_PACKAGE,
    CB_REFRESH_PROFILE,
    CB_BACK_TO_PROFILE,
}

ACTIVE_PACKAGE_MSG = (
    "У вас уже есть активный пакет.\n\n"
    "Сначала необходимо получить весь объём оплаченных контактов."
)


async def render_profile(
    target: Message,
    *,
    telegram_id: int | None = None,
    edit: bool = False,
) -> None:
    uid = telegram_id if telegram_id is not None else target.from_user.id
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, uid)
        if not user:
            text = "Нажмите /start"
            kb = None
        else:
            data = await load_profile_data(session, user.id)
            if not data:
                text = "У вас нет активного пакета.\n\nВыберите тариф, чтобы начать."
                kb = no_package_keyboard()
            elif data.is_completed:
                text = format_completed_text(data)
                kb = completed_keyboard()
            else:
                text = format_cabinet_text(data)
                kb = cabinet_keyboard()

    if edit:
        await target.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data.in_(PROFILE_CALLBACKS))
async def cb_profile(callback: CallbackQuery) -> None:
    await render_profile(
        callback.message,
        telegram_id=callback.from_user.id,
        edit=True,
    )
    if callback.data == CB_REFRESH_PROFILE:
        await callback.answer("Данные обновлены")
    else:
        await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    await render_profile(message)


@router.callback_query(F.data == CB_MY_COMPETITORS)
async def cb_my_competitors(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return

        order = await get_active_order(session, user.id)
        data = await load_profile_data(session, user.id)
        if not order and not data:
            await callback.answer("Сначала оплатите пакет", show_alert=True)
            return

        text, total = await get_competitors_view(session, user.id)

    if total == 0:
        text = (
            "📱 <b>Ваши конкуренты</b>\n\n"
            "Всего номеров:\n0\n\n"
            "Вы ещё не добавили номера конкурентов."
        )

    await callback.message.edit_text(text, reply_markup=competitors_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({CB_BUY_PACKAGE, CB_BUY_NEW}))
async def cb_buy_package(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        active = await get_active_order(session, user.id)

    if active:
        await callback.answer(ACTIVE_PACKAGE_MSG, show_alert=True)
        return

    from services.messages import PACKAGES_INTRO_TEXT
    from keyboards.menu_keyboard import packages_list_keyboard

    await state.clear()
    await callback.message.edit_text(PACKAGES_INTRO_TEXT, reply_markup=packages_list_keyboard())
    await callback.answer()
