from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from database.database import async_session
from handlers.brief import start_brief_flow
from keyboards.package_payment_keyboard import package_card_actions_keyboard
from keyboards.menu_keyboard import (
    CB_MAIN_TRIAL,
    CB_PKG_DISCUSS,
    CB_PKG_LIST,
    CB_PKG_PREFIX,
    CB_PKG_TRIAL_CARD,
    CB_PKG_TRIAL_START,
    packages_list_keyboard,
    trial_card_keyboard,
)
from services.brief_service import get_latest_submitted_brief
from services.messages import PACKAGES_INTRO_TEXT, TRIAL_CARD_TEXT
from services.package_catalog import get_package
from services.user_service import get_user_by_telegram_id

router = Router()


def _format_price(amount: int) -> str:
    return f"{amount:,} ₽".replace(",", " ")


def package_detail_text(code: str) -> str | None:
    pkg = get_package(code)
    if not pkg or pkg.is_trial:
        return None
    unit = _format_price(pkg.unit_price)
    total = _format_price(pkg.price)
    return (
        f"<b>{pkg.name}</b>\n\n"
        f"Объём: {pkg.contact_count} контактов\n"
        f"Стоимость: {total}\n"
        f"Цена контакта: {unit}\n\n"
        "Входит: настройка согласованных источников, подбор новых контактов "
        "и постепенная выдача через Telegram.\n\n"
        "Срок выдачи и правила замены согласуем до оплаты. Скорость поступления зависит "
        "от активности выбранных источников и доступности контактов."
    )


@router.callback_query(F.data == CB_PKG_TRIAL_CARD)
async def cb_trial_card(callback: CallbackQuery) -> None:
    await callback.message.edit_text(TRIAL_CARD_TEXT, reply_markup=trial_card_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_PKG_LIST)
async def cb_pkg_list(callback: CallbackQuery) -> None:
    await callback.message.edit_text(PACKAGES_INTRO_TEXT, reply_markup=packages_list_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PKG_PREFIX))
async def cb_pkg_detail(callback: CallbackQuery) -> None:
    code = callback.data.removeprefix(CB_PKG_PREFIX)
    text = package_detail_text(code)
    if not text:
        await callback.answer("Пакет не найден", show_alert=True)
        return
    await callback.message.edit_text(text, reply_markup=package_card_actions_keyboard(code))
    await callback.answer()


async def _start_trial_brief(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        submitted = await get_latest_submitted_brief(session, user.id)
    if submitted:
        from services.admin_notify_service import notify_admin_trial_interest

        await notify_admin_trial_interest(user, submitted.request_code)
        await callback.message.answer(
            "Вы уже отправляли вводные. Команда получила запрос на триал и свяжется с вами в Telegram.",
        )
        return
    await start_brief_flow(callback.message, callback.from_user.id, is_trial=True, edit=True)


@router.callback_query(F.data == CB_MAIN_TRIAL)
@router.callback_query(F.data == CB_PKG_TRIAL_START)
async def cb_trial_start(callback: CallbackQuery) -> None:
    await _start_trial_brief(callback)
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PKG_DISCUSS))
async def cb_discuss_package(callback: CallbackQuery) -> None:
    code = callback.data.removeprefix(CB_PKG_DISCUSS)
    pkg = get_package(code)
    if not pkg or pkg.is_trial:
        await callback.answer("Пакет не найден", show_alert=True)
        return

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        submitted = await get_latest_submitted_brief(session, user.id)

    if submitted:
        from services.admin_notify_service import notify_admin_package_interest

        await notify_admin_package_interest(user, submitted.request_code, pkg.name)
        await callback.message.answer(
            f"Интерес к пакету «{pkg.name}» передан команде. Мы свяжемся с вами в Telegram.",
        )
        await callback.answer()
        return

    await start_brief_flow(
        callback.message,
        callback.from_user.id,
        is_trial=False,
        package_code=code,
        edit=False,
    )
    await callback.answer()
