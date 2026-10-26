"""Сценарий оплаты по инструкции — через бриф и команду. Кнопки «купить» ведут в пакеты."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.start_keyboard import CB_BUY_NEW, CB_CHOOSE_PACKAGE
from services.messages import PACKAGES_INTRO_TEXT
from keyboards.menu_keyboard import packages_list_keyboard

router = Router()


@router.callback_query(F.data.in_({CB_CHOOSE_PACKAGE, CB_BUY_NEW}))
async def cb_legacy_buy(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(PACKAGES_INTRO_TEXT, reply_markup=packages_list_keyboard())
    await callback.answer()

