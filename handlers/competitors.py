from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from database.database import async_session
from keyboards.start_keyboard import CB_ADD_COMPETITORS, active_user_keyboard
from services.competitor_service import add_competitors, count_competitors
from services.user_service import get_active_order, get_user_by_telegram_id
from utils.logger import get_logger
from utils.phone import extract_phones, normalize_phone

logger = get_logger(__name__)
router = Router()


class AddCompetitorsState(StatesGroup):
    waiting = State()


def _share_contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📇 Отправить контакт", request_contact=True)],
            [KeyboardButton(text="✅ Готово")],
        ],
        resize_keyboard=True,
    )


ADD_COMPETITORS_TEXT = """📱 <b>Добавление конкурентов</b>

Отправьте номера конкурентов одним из способов:

• Нажмите «📇 Отправить контакт» и выберите контакт из телефонной книги
• Или отправьте номер текстом: <code>+79991234567</code>
• Можно несколько номеров — каждый с новой строки

Когда закончите — нажмите «✅ Готово»."""


@router.callback_query(F.data == CB_ADD_COMPETITORS)
async def cb_add_competitors(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return

        active_order = await get_active_order(session, user.id)
        if not active_order:
            await callback.answer(
                "Сначала оплатите пакет через «Выбрать пакет»",
                show_alert=True,
            )
            return

        total = await count_competitors(session, user.id)

    await state.set_state(AddCompetitorsState.waiting)
    await callback.message.answer(
        ADD_COMPETITORS_TEXT + f"\n\nУже добавлено: <b>{total}</b>",
        reply_markup=_share_contact_keyboard(),
    )
    await callback.answer()


@router.message(AddCompetitorsState.waiting, F.contact)
async def receive_contact(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.contact.phone_number or "")
    if not phone:
        await message.answer("⚠️ Не удалось распознать номер. Попробуйте другой контакт.")
        return
    await _save_phones(message, state, [phone])


@router.message(AddCompetitorsState.waiting, F.text == "✅ Готово")
async def finish_adding(message: Message, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        total = await count_competitors(session, user.id) if user else 0

    await state.clear()
    await message.answer(
        f"✅ Готово! Всего конкурентов: <b>{total}</b>",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("Главное меню:", reply_markup=active_user_keyboard())


@router.message(AddCompetitorsState.waiting, F.text)
async def receive_text_phones(message: Message, state: FSMContext) -> None:
    phones = extract_phones(message.text or "")
    if not phones:
        await message.answer(
            "⚠️ Не найдено номеров. Формат: +79991234567 или отправьте контакт кнопкой ниже."
        )
        return
    await _save_phones(message, state, phones)


async def _save_phones(message: Message, state: FSMContext, phones: list[str]) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await state.clear()
            await message.answer("Нажмите /start", reply_markup=ReplyKeyboardRemove())
            return

        active_order = await get_active_order(session, user.id)
        if not active_order:
            await state.clear()
            await message.answer(
                "❌ Пакет не активен. Оплатите тариф через /start",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        result = await add_competitors(session, user.id, phones)
        total = await count_competitors(session, user.id)

    lines = [f"✅ Добавлено: {result.saved}"]
    if result.duplicates:
        lines.append(f"⚠️ Уже были в списке: {result.duplicates}")
    lines.append(f"Всего конкурентов: {total}")
    lines.append("\nМожете отправить ещё или нажать «✅ Готово».")
    await message.answer("\n".join(lines))
