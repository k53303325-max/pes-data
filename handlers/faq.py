from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.menu_keyboard import CB_FAQ_EVAL, CB_FAQ_LIST, CB_FAQ_PREFIX, faq_answer_keyboard, faq_list_keyboard
from services.faq_content import FAQ_ANSWERS, FAQ_TOPICS
from services.messages import FAQ_LIST_INTRO

router = Router()


@router.callback_query(F.data == CB_FAQ_LIST)
async def cb_faq_list(callback: CallbackQuery) -> None:
    await callback.message.edit_text(FAQ_LIST_INTRO, reply_markup=faq_list_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_FAQ_EVAL)
@router.callback_query(F.data.startswith(CB_FAQ_PREFIX))
async def cb_faq_item(callback: CallbackQuery) -> None:
    key = callback.data.removeprefix(CB_FAQ_PREFIX) if callback.data.startswith(CB_FAQ_PREFIX) else "eval"
    if callback.data == CB_FAQ_EVAL:
        key = "eval"
    answer = FAQ_ANSWERS.get(key)
    if not answer:
        await callback.answer()
        return
    title = next((t for k, t in FAQ_TOPICS if k == key), "Вопрос")
    await callback.message.edit_text(f"<b>{title}</b>\n\n{answer}", reply_markup=faq_answer_keyboard())
    await callback.answer()
