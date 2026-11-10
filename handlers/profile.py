from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from handlers.project import ProjectNameState

from database.database import async_session
from keyboards.profile_keyboard import (
    CB_BACK_TO_PROFILE,
    CB_BUY_PACKAGE,
    CB_MY_COMPETITORS,
    CB_MY_PACKAGE,
    CB_MY_PROJECTS,
    CB_PROFILE,
    CB_PROJECT_CREATE,
    CB_PROJECT_OPEN_PREFIX,
    CB_REFRESH_PROFILE,
    cabinet_keyboard,
    completed_keyboard,
    no_package_keyboard,
    project_detail_keyboard,
    projects_list_keyboard,
)
from keyboards.start_keyboard import CB_BUY_NEW
from services.profile_service import (
    format_cabinet_text,
    format_completed_text,
    format_project_need_name_text,
    format_projects_list_text,
    get_project_detail_view,
    load_profile_data,
)
from services.project_service import (
    create_additional_project,
    list_projects_for_active_order,
)
from services.user_service import get_active_order, get_user_by_telegram_id
from utils.logger import get_logger
from utils.telegram_messages import respond_to_callback, safe_edit_or_send

logger = get_logger(__name__)
router = Router()

PROFILE_CALLBACKS = {
    CB_PROFILE,
    CB_MY_PACKAGE,
    CB_REFRESH_PROFILE,
    CB_BACK_TO_PROFILE,
}

ACTIVE_PACKAGE_MSG = (
    "У вас уже есть активный пакет.\n\n"
    "Сначала необходимо получить весь объём оплаченных контактов."
)


async def render_profile(
    target: Message,
    *,
    telegram_id: int | None = None,
    edit: bool = False,
) -> None:
    uid = telegram_id if telegram_id is not None else target.from_user.id
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, uid)
        if not user:
            text = "Нажмите /start"
            kb = None
        else:
            data = await load_profile_data(session, user.id)
            if not data:
                text = "У вас нет активного пакета.\n\nВыберите тариф, чтобы начать."
                kb = no_package_keyboard()
            elif data.is_completed:
                text = format_completed_text(data)
                kb = completed_keyboard()
            else:
                text = format_cabinet_text(data)
                kb = cabinet_keyboard()

    if edit:
        await safe_edit_or_send(target, text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


async def _profile_text_and_keyboard(telegram_id: int) -> tuple[str, object | None]:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return "Нажмите /start", None
        data = await load_profile_data(session, user.id)
        if not data:
            return (
                "У вас нет активного пакета.\n\nВыберите тариф, чтобы начать.",
                no_package_keyboard(),
            )
        if data.is_completed:
            return format_completed_text(data), completed_keyboard()
        return format_cabinet_text(data), cabinet_keyboard()


@router.callback_query(F.data.in_(PROFILE_CALLBACKS))
async def cb_profile(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text, kb = await _profile_text_and_keyboard(callback.from_user.id)
    if callback.data == CB_REFRESH_PROFILE:
        await respond_to_callback(callback, text, reply_markup=kb, ack=False)
        await callback.answer("Данные обновлены")
    else:
        await respond_to_callback(callback, text, reply_markup=kb)


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    await render_profile(message)


async def _render_projects_hub(
    callback: CallbackQuery, state: FSMContext, user_id: int
) -> None:
    async with async_session() as session:
        projects = await list_projects_for_active_order(session, user_id)

    await state.update_data(current_project_id=None)

    if len(projects) > 1:
        text = format_projects_list_text(projects)
        kb = projects_list_keyboard(projects)
        await state.clear()
        await respond_to_callback(callback, text, reply_markup=kb)
        return

    if len(projects) == 1:
        project = projects[0]
        await state.update_data(current_project_id=project.id)
        async with async_session() as session:
            text, needs_name, can_add = await get_project_detail_view(
                session, user_id, project.id
            )
        if needs_name:
            await state.set_state(ProjectNameState.waiting)
        else:
            await state.clear()
            await state.update_data(current_project_id=project.id)
        await respond_to_callback(
            callback,
            text,
            reply_markup=project_detail_keyboard(
                can_add_numbers=can_add,
                show_create=True,
                projects_count=1,
            ),
        )
        return

    text = format_projects_list_text([])
    kb = projects_list_keyboard([])
    await state.clear()
    await respond_to_callback(callback, text, reply_markup=kb)


@router.callback_query(F.data.in_({CB_MY_PROJECTS, CB_MY_COMPETITORS}))
async def cb_my_projects(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return

        order = await get_active_order(session, user.id)
        if not order:
            await callback.answer("Сначала оплатите пакет", show_alert=True)
            return

    await _render_projects_hub(callback, state, user.id)


@router.callback_query(F.data.startswith(CB_PROJECT_OPEN_PREFIX))
async def cb_project_open(callback: CallbackQuery, state: FSMContext) -> None:
    project_id = int(callback.data.removeprefix(CB_PROJECT_OPEN_PREFIX))
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        projects = await list_projects_for_active_order(session, user.id)
        text, needs_name, can_add = await get_project_detail_view(
            session, user.id, project_id
        )

    await state.update_data(current_project_id=project_id)
    if needs_name:
        await state.set_state(ProjectNameState.waiting)
    else:
        await state.clear()
        await state.update_data(current_project_id=project_id)

    await respond_to_callback(
        callback,
        text,
        reply_markup=project_detail_keyboard(
            can_add_numbers=can_add,
            show_create=True,
            projects_count=len(projects),
        ),
    )


@router.callback_query(F.data == CB_PROJECT_CREATE)
async def cb_project_create(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        order = await get_active_order(session, user.id)
        if not order:
            await callback.answer("Сначала оплатите пакет", show_alert=True)
            return
        project = await create_additional_project(session, user, order)
        project_id = project.id

    await state.set_state(ProjectNameState.waiting)
    await state.update_data(current_project_id=project_id)
    text = format_project_need_name_text()
    await respond_to_callback(
        callback,
        text,
        reply_markup=project_detail_keyboard(
            can_add_numbers=False,
            show_create=False,
            projects_count=2,
        ),
    )


@router.callback_query(F.data.in_({CB_BUY_PACKAGE, CB_BUY_NEW}))
async def cb_buy_package(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        active = await get_active_order(session, user.id)

    if active:
        await callback.answer(ACTIVE_PACKAGE_MSG, show_alert=True)
        return

    from services.messages import PACKAGES_INTRO_TEXT
    from keyboards.menu_keyboard import packages_list_keyboard

    await state.clear()
    await callback.answer()
    await callback.message.edit_text(PACKAGES_INTRO_TEXT, reply_markup=packages_list_keyboard())
