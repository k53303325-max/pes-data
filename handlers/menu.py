from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config.settings import settings
from keyboards.menu_keyboard import (
    CB_MAIN_CONTACT,
    CB_MAIN_FAQ,
    CB_MAIN_HOW,
    CB_MAIN_MENU,
    CB_MAIN_NICHE,
    CB_MAIN_PACKAGES,
    CB_MAIN_REFERRAL,
    CB_MAIN_TRIAL,
    contact_keyboard,
    faq_list_keyboard,
    how_it_works_keyboard,
    main_menu_keyboard,
    packages_list_keyboard,
)
from services.messages import (
    CONTACT_TEXT,
    FAQ_LIST_INTRO,
    HOW_IT_WORKS_TEXT,
    PACKAGES_INTRO_TEXT,
    WELCOME_TEXT,
)
from utils.logger import get_logger
from utils.telegram_messages import respond_to_callback, safe_edit_or_send

logger = get_logger(__name__)
router = Router()


async def show_main_menu_message(message, *, edit: bool = False) -> None:
    kb = main_menu_keyboard()
    if edit:
        await safe_edit_or_send(message, WELCOME_TEXT, reply_markup=kb)
    else:
        await message.answer(WELCOME_TEXT, reply_markup=kb)


@router.callback_query(F.data == CB_MAIN_MENU)
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await respond_to_callback(callback, WELCOME_TEXT, reply_markup=main_menu_keyboard(), ack=False)


@router.callback_query(F.data.in_({CB_MAIN_HOW, "how_it_works"}))
async def cb_how(callback: CallbackQuery) -> None:
    await respond_to_callback(
        callback,
        HOW_IT_WORKS_TEXT,
        reply_markup=how_it_works_keyboard(),
        ack=False,
    )


@router.callback_query(F.data.in_({CB_MAIN_PACKAGES, "choose_tariff", "buy_package"}))
async def cb_packages_menu(callback: CallbackQuery) -> None:
    await respond_to_callback(
        callback,
        PACKAGES_INTRO_TEXT,
        reply_markup=packages_list_keyboard(),
        ack=False,
    )


@router.callback_query(F.data.in_({CB_MAIN_FAQ, "faq"}))
async def cb_faq_list(callback: CallbackQuery) -> None:
    await respond_to_callback(
        callback,
        FAQ_LIST_INTRO,
        reply_markup=faq_list_keyboard(),
        ack=False,
    )


@router.callback_query(F.data == CB_MAIN_CONTACT)
async def cb_contact(callback: CallbackQuery) -> None:
    username = settings.admin_username or "markusvalerius"
    await respond_to_callback(
        callback,
        CONTACT_TEXT,
        reply_markup=contact_keyboard(username),
        ack=False,
    )


@router.callback_query(F.data == CB_MAIN_TRIAL)
async def cb_main_trial(callback: CallbackQuery, state: FSMContext) -> None:
    from handlers.packages import handle_trial_start

    await state.clear()
    await handle_trial_start(callback)


@router.callback_query(F.data == CB_MAIN_NICHE)
async def cb_main_niche(callback: CallbackQuery, state: FSMContext) -> None:
    from handlers.brief import handle_niche_start

    await state.clear()
    await handle_niche_start(callback)


@router.callback_query(F.data == CB_MAIN_REFERRAL)
async def cb_main_referral(callback: CallbackQuery, state: FSMContext) -> None:
    from handlers.referral import handle_referral_program

    await state.clear()
    await handle_referral_program(callback)
