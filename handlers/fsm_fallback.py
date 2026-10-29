from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.menu_keyboard import main_menu_keyboard
from utils.fsm_filters import HasStateFilter

router = Router()

FSM_HINT = (
    "Не понял сообщение в текущем шаге.\n\n"
    "Используйте кнопки под последним сообщением бота, «Назад» или /start — "
    "вернёт в главное меню и сбросит незавершённый ввод."
)


@router.message(HasStateFilter())
async def fsm_unhandled_message(message: Message, state: FSMContext) -> None:
    await message.answer(FSM_HINT, reply_markup=main_menu_keyboard())
