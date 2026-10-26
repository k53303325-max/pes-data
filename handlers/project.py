from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from database.database import async_session
from keyboards.competitor_keyboard import project_created_keyboard
from services.project_service import (
    PROJECT_NAME_PROMPT,
    get_project_needing_name,
    project_created_text,
    set_project_name,
)
from services.user_service import get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


class ProjectNameState(StatesGroup):
    waiting = State()


class NeedsProjectName(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not message.from_user or not message.text or message.text.startswith("/"):
            return False
        async with async_session() as session:
            user = await get_user_by_telegram_id(session, message.from_user.id)
            if not user:
                return False
            project = await get_project_needing_name(session, user.id)
            return project is not None


async def prompt_project_name(target: Message, *, edit: bool = False) -> None:
    if edit:
        await target.edit_text(PROJECT_NAME_PROMPT)
    else:
        await target.answer(PROJECT_NAME_PROMPT)


async def start_project_name_flow(
    target: Message,
    state: FSMContext,
    *,
    user_id: int,
    edit: bool = False,
) -> None:
    async with async_session() as session:
        project = await get_project_needing_name(session, user_id)
        if not project:
            return

    await state.set_state(ProjectNameState.waiting)
    await prompt_project_name(target, edit=edit)


async def _save_project_name(message: Message, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await state.clear()
            await message.answer("Нажмите /start")
            return

        project = await get_project_needing_name(session, user.id)
        if not project:
            await state.clear()
            return

        try:
            project = await set_project_name(session, project, message.text or "")
        except ValueError as exc:
            await message.answer(f"⚠️ {exc}\n\nВведите название ещё раз:")
            return

        from services.admin_notify_service import notify_admin_new_project

        await notify_admin_new_project(user, project.project_name or "")

    await state.clear()
    await message.answer(
        project_created_text(project.project_name or ""),
        reply_markup=project_created_keyboard(),
    )


@router.message(ProjectNameState.waiting, F.text)
async def receive_project_name(message: Message, state: FSMContext) -> None:
    await _save_project_name(message, state)


@router.message(NeedsProjectName(), F.text)
async def receive_project_name_fallback(message: Message, state: FSMContext) -> None:
    await state.set_state(ProjectNameState.waiting)
    await _save_project_name(message, state)
