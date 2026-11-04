from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.menu_keyboard import main_menu_keyboard
from utils.fsm_filters import HasStateFilter
from utils.logger import get_logger
from utils.telegram_messages import respond_to_callback

logger = get_logger(__name__)
router = Router()

FSM_HINT = (
    "Не понял сообщение в текущем шаге.\n\n"
    "Используйте кнопки под последним сообщением бота, «Назад» или /start — "
    "вернёт в главное меню и сбросит незавершённый ввод."
)


@router.message(HasStateFilter())
async def fsm_unhandled_message(message: Message, state: FSMContext) -> None:
    await message.answer(FSM_HINT, reply_markup=main_menu_keyboard())


@router.callback_query()
async def fsm_unhandled_callback(callback: CallbackQuery) -> None:
    logger.warning(
        "Unhandled callback data=%r telegram_id=%s",
        callback.data,
        callback.from_user.id,
    )
    await respond_to_callback(
        callback,
        "Меню устарело. Нажмите /start для новой клавиатуры.",
        reply_markup=main_menu_keyboard(),
    )
