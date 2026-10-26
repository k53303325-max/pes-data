from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from database.database import async_session
from keyboards.competitor_keyboard import CB_ADD_COMPETITORS, CB_ADD_MORE, after_save_keyboard
from handlers.project import ProjectNameState
from services.competitor_service import format_process_result, save_competitors
from services.project_service import get_active_project, get_project_needing_name, PROJECT_NAME_PROMPT
from services.user_service import get_active_order, get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


class AddCompetitorsState(StatesGroup):
    waiting = State()


INPUT_COMPETITORS_TEXT = (
    "📱 <b>Отправьте номера телефонов конкурентов.</b>\n\n"
    "Каждый номер необходимо указать с новой строки.\n\n"
    "Пример:\n\n"
    "<code>79991234567</code>\n"
    "<code>79997654321</code>\n"
    "<code>79995556677</code>\n\n"
    "Другие форматы ввода не поддерживаются."
)


async def _start_input_mode(
    target: Message,
    state: FSMContext,
    *,
    telegram_id: int,
) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await target.answer("Нажмите /start")
            return
        order = await get_active_order(session, user.id)
        if not order:
            await target.answer("Сначала оплатите пакет через «Выбрать пакет»")
            return

        pending = await get_project_needing_name(session, user.id)
        if pending:
            await state.set_state(ProjectNameState.waiting)
            await target.answer(
                f"Сначала укажите название проекта.\n\n{PROJECT_NAME_PROMPT}"
            )
            return

    await state.set_state(AddCompetitorsState.waiting)
    await target.answer(INPUT_COMPETITORS_TEXT, reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data.in_({CB_ADD_COMPETITORS, CB_ADD_MORE}))
async def cb_add_competitors(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_input_mode(
        callback.message,
        state,
        telegram_id=callback.from_user.id,
    )
    await callback.answer()


@router.message(AddCompetitorsState.waiting, F.text)
async def receive_competitor_numbers(message: Message, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await state.clear()
            await message.answer("Нажмите /start")
            return

        order = await get_active_order(session, user.id)
        if not order:
            await state.clear()
            await message.answer("❌ Пакет не активен. Оплатите тариф через /start")
            return

        project = await get_active_project(session, user.id)
        result = await save_competitors(
            session,
            user.id,
            message.text or "",
            project_id=project.id if project else None,
            added_by=user.username or user.first_name or "user",
        )

        if result.added > 0 and project:
            from services.admin_notify_service import notify_admin_competitors_added

            await notify_admin_competitors_added(
                user,
                project_name=project.project_name,
                added=result.added,
                total=result.total_active,
            )

    await state.clear()

    if result.lines_received == 0:
        await message.answer(
            "⚠️ Не найдено номеров. Отправьте номера — каждый с новой строки, "
            "формат: <code>79991234567</code>",
            reply_markup=after_save_keyboard(),
        )
        return

    if result.added == 0 and result.already_tracked == 0 and result.invalid == result.lines_received:
        await message.answer(
            "⚠️ Ни один номер не прошёл проверку.\n\n"
            "Поддерживаются только номера из 11 цифр, начинающиеся с 7.",
            reply_markup=after_save_keyboard(),
        )
        return

    await message.answer(
        format_process_result(result),
        reply_markup=after_save_keyboard(),
    )
