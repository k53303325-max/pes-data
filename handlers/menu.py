from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.menu_keyboard import (
    CB_MAIN_CONTACT,
    CB_MAIN_FAQ,
    CB_MAIN_HOW,
    CB_MAIN_MENU,
    CB_MAIN_PACKAGES,
    contact_keyboard,
    faq_list_keyboard,
    how_it_works_keyboard,
    main_menu_keyboard,
    packages_list_keyboard,
)
from services.messages import CONTACT_TEXT, FAQ_LIST_INTRO, HOW_IT_WORKS_TEXT, PACKAGES_INTRO_TEXT, WELCOME_TEXT
from config.settings import settings

router = Router()


async def show_main_menu_message(message, *, edit: bool = False) -> None:
    kb = main_menu_keyboard()
    if edit:
        await message.edit_text(WELCOME_TEXT, reply_markup=kb)
    else:
        await message.answer(WELCOME_TEXT, reply_markup=kb)


@router.callback_query(F.data == CB_MAIN_MENU)
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_main_menu_message(callback.message, edit=True)
    await callback.answer()


@router.callback_query(F.data.in_({CB_MAIN_HOW, "how_it_works"}))
async def cb_how(callback: CallbackQuery) -> None:
    await callback.message.edit_text(HOW_IT_WORKS_TEXT, reply_markup=how_it_works_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({CB_MAIN_PACKAGES, "choose_tariff", "buy_package"}))
async def cb_packages(callback: CallbackQuery) -> None:
    await callback.message.edit_text(PACKAGES_INTRO_TEXT, reply_markup=packages_list_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({CB_MAIN_FAQ, "faq"}))
async def cb_faq_list(callback: CallbackQuery) -> None:
    await callback.message.edit_text(FAQ_LIST_INTRO, reply_markup=faq_list_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_MAIN_CONTACT)
async def cb_contact(callback: CallbackQuery) -> None:
    username = settings.admin_username or "markusvalerius"
    await callback.message.edit_text(CONTACT_TEXT, reply_markup=contact_keyboard(username))
    await callback.answer()
