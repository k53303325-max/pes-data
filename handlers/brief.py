from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from database.models import BriefRequestStatus, NicheBriefRequest
from keyboards.menu_keyboard import (
    CB_BRIEF_COMP_HELP,
    CB_BRIEF_CONFIRM,
    CB_BRIEF_EDIT,
    CB_BRIEF_EDIT_PREFIX,
    CB_BRIEF_INN_NO,
    CB_BRIEF_RESUBMIT,
    CB_BRIEF_SALES_PREFIX,
    CB_BRIEF_START,
    CB_MAIN_MENU,
    CB_MAIN_NICHE,
    brief_competitors_keyboard,
    brief_edit_fields_keyboard,
    brief_failed_keyboard,
    brief_inn_keyboard,
    back_to_main_keyboard,
    brief_intro_keyboard,
    brief_sales_keyboard,
    brief_success_keyboard,
    brief_summary_keyboard,
    trial_blocked_keyboard,
)
from services.brief_service import (
    SALES_LABELS,
    check_trial_inn,
    format_summary,
    get_draft_brief,
    get_or_create_draft,
    infer_brief_step,
    parse_competitor_input,
    phones_to_storage,
    submit_brief,
    validate_inn_field,
)
from services.messages import (
    BOT_SYSTEM_ERROR_TEXT,
    BRIEF_FAILED_TEXT,
    BRIEF_INN_INVALID,
    BRIEF_INN_NO_HELP,
    BRIEF_INN_TEXT,
    BRIEF_INTRO_TEXT,
    BRIEF_Q1_EMPTY,
    BRIEF_Q1_TEXT,
    BRIEF_Q2_TEXT,
    BRIEF_Q3_TEXT,
    BRIEF_SALES_NONE_NOTE,
    BRIEF_SUBMIT_FOOTER,
    BRIEF_SUCCESS_TEXT,
    TRIAL_BLOCK_INN_ACTIVE,
    TRIAL_BLOCK_INN_USED,
    TRIAL_BLOCK_TELEGRAM,
)
from services.user_service import get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


class BriefState(StatesGroup):
    business = State()
    sales = State()
    competitors = State()
    inn = State()
    inn_manual = State()
    summary = State()
    edit_menu = State()


async def start_brief_flow(
    message,
    telegram_id: int,
    *,
    is_trial: bool,
    package_code: str | None = None,
    edit: bool = False,
) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return
        draft = await get_or_create_draft(
            session,
            user,
            is_trial=is_trial,
            package_code=package_code,
            source=user.start_source,
        )

    text = BRIEF_INTRO_TEXT
    kb = brief_intro_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == CB_MAIN_NICHE)
async def cb_niche(callback: CallbackQuery) -> None:
    await start_brief_flow(callback.message, callback.from_user.id, is_trial=False, edit=True)
    await callback.answer()


@router.callback_query(F.data == CB_BRIEF_START)
async def cb_brief_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BriefState.business)
    await callback.message.edit_text(BRIEF_Q1_TEXT, reply_markup=back_to_main_keyboard())
    await callback.answer()


@router.message(BriefState.business, F.text)
async def brief_business(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer(BRIEF_Q1_EMPTY)
        return

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        draft = await get_draft_brief(session, user.id)
        if not draft:
            draft = await get_or_create_draft(session, user, is_trial=False, package_code=None, source=None)
        draft.business_text = text
        await session.commit()

    await state.set_state(BriefState.sales)
    await message.answer(BRIEF_Q2_TEXT, reply_markup=brief_sales_keyboard())


@router.callback_query(F.data.startswith(CB_BRIEF_SALES_PREFIX), BriefState.sales)
async def brief_sales(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.removeprefix(CB_BRIEF_SALES_PREFIX)
    if key not in SALES_LABELS:
        await callback.answer()
        return

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        draft = await get_draft_brief(session, user.id)
        if draft:
            draft.sales_team = key
            await session.commit()

    if key == "none":
        await callback.message.answer(BRIEF_SALES_NONE_NOTE)

    await state.set_state(BriefState.competitors)
    await callback.message.answer(BRIEF_Q3_TEXT, reply_markup=brief_competitors_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_BRIEF_COMP_HELP, BriefState.competitors)
async def brief_comp_help(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if user:
            draft = await get_draft_brief(session, user.id)
            if draft:
                draft.competitors_need_help = True
                draft.competitor_phones_raw = "нужна помощь"
                draft.competitor_phones_normalized = None
                await session.commit()
                await _goto_after_competitors(callback.message, state, draft, user, edit=False)
    await callback.answer()


@router.message(BriefState.competitors, F.text)
async def brief_competitors(message: Message, state: FSMContext) -> None:
    phones, bad, _ = parse_competitor_input(message.text or "")
    if bad and not phones:
        await message.answer(
            f'Не удалось распознать номер «{bad}». Проверьте его и пришлите ещё раз, '
            "желательно с кодом страны. Остальные ответы сохранены.",
            reply_markup=brief_competitors_keyboard(),
        )
        return
    if not phones:
        await message.answer(
            "Пришлите хотя бы один номер телефона конкурента или нажмите «Нужна помощь с выбором».",
            reply_markup=brief_competitors_keyboard(),
        )
        return

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        draft = await get_draft_brief(session, user.id)
        if not draft:
            return
        draft.competitors_need_help = False
        draft.competitor_phones_raw = message.text.strip()
        draft.competitor_phones_normalized = phones_to_storage(phones)
        await session.commit()
        await _goto_after_competitors(message, state, draft, user, edit=False)


async def _goto_after_competitors(
    message,
    state: FSMContext,
    draft: NicheBriefRequest,
    user,
    *,
    edit: bool,
) -> None:
    if draft.is_trial and not draft.inn and not draft.inn_manual_review:
        await state.set_state(BriefState.inn)
        text = BRIEF_INN_TEXT
        kb = brief_inn_keyboard()
        await message.answer(text, reply_markup=kb)
        return
    await _show_summary(message, state, user.telegram_id)


async def _process_inn_input(message: Message, state: FSMContext) -> None:
    ok, inn = validate_inn_field(message.text or "")
    if not ok or not inn:
        await message.answer(BRIEF_INN_INVALID, reply_markup=brief_inn_keyboard())
        return

    try:
        async with async_session() as session:
            user = await get_user_by_telegram_id(session, message.from_user.id)
            if not user:
                await message.answer(BOT_SYSTEM_ERROR_TEXT)
                return
            check = await check_trial_inn(session, user, inn)
            if not check.ok:
                await _trial_block_message(message, check.reason or "")
                return
            draft = await get_draft_brief(session, user.id)
            if not draft:
                await message.answer("Начните бриф заново: /start → «Проверить мою нишу».")
                return
            draft.inn = inn
            draft.inn_manual_review = False
            draft.inn_manual_details = None
            await session.commit()

        await _show_summary(message, state, message.from_user.id)
    except Exception:
        logger.exception("brief_inn failed telegram_id=%s", message.from_user.id)
        await message.answer(BOT_SYSTEM_ERROR_TEXT)


@router.message(BriefState.inn, F.text)
async def brief_inn(message: Message, state: FSMContext) -> None:
    await _process_inn_input(message, state)


@router.callback_query(F.data == CB_BRIEF_INN_NO, BriefState.inn)
async def brief_inn_no(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if user:
            draft = await get_draft_brief(session, user.id)
            if draft:
                draft.inn_manual_review = True
                draft.inn = None
                await session.commit()
    await state.set_state(BriefState.inn_manual)
    await callback.message.edit_text(BRIEF_INN_NO_HELP, reply_markup=brief_inn_keyboard())
    await callback.answer()


@router.message(BriefState.inn_manual, F.text)
async def brief_inn_manual_details(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("Напишите название компании или добавьте сайт.")
        return
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user:
            draft = await get_draft_brief(session, user.id)
            if draft:
                draft.inn_manual_details = text
                await session.commit()
    await _show_summary(message, state, message.from_user.id)


async def _trial_block_message(message, reason: str) -> None:
    if reason == "inn_active":
        text = TRIAL_BLOCK_INN_ACTIVE
    elif reason == "inn_used":
        text = TRIAL_BLOCK_INN_USED
    else:
        text = TRIAL_BLOCK_TELEGRAM
    await message.answer(text, reply_markup=trial_blocked_keyboard())


async def _show_summary(message, state: FSMContext, telegram_id: int) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await message.answer(BOT_SYSTEM_ERROR_TEXT)
            return
        draft = await get_draft_brief(session, user.id)
        if not draft:
            await message.answer("Черновик брифа не найден. Начните с /start.")
            return
        body = format_summary(draft)
    await state.set_state(BriefState.summary)
    await message.answer(body + BRIEF_SUBMIT_FOOTER, reply_markup=brief_summary_keyboard())


@router.callback_query(F.data == CB_BRIEF_EDIT)
async def brief_edit_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        show_inn = False
        if user:
            draft = await get_draft_brief(session, user.id)
            show_inn = bool(draft and draft.is_trial)
    await state.set_state(BriefState.edit_menu)
    await callback.message.edit_text(
        "Что изменить?",
        reply_markup=brief_edit_fields_keyboard(show_inn=show_inn),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_BRIEF_EDIT_PREFIX))
async def brief_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.removeprefix(CB_BRIEF_EDIT_PREFIX)
    if field == "business":
        await state.set_state(BriefState.business)
        await callback.message.edit_text(BRIEF_Q1_TEXT, reply_markup=back_to_main_keyboard())
    elif field == "sales":
        await state.set_state(BriefState.sales)
        await callback.message.edit_text(BRIEF_Q2_TEXT, reply_markup=brief_sales_keyboard())
    elif field == "phones":
        await state.set_state(BriefState.competitors)
        await callback.message.edit_text(BRIEF_Q3_TEXT, reply_markup=brief_competitors_keyboard())
    elif field == "inn":
        await state.set_state(BriefState.inn)
        await callback.message.edit_text(BRIEF_INN_TEXT, reply_markup=brief_inn_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_BRIEF_CONFIRM)
@router.callback_query(F.data == CB_BRIEF_RESUBMIT)
async def brief_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        draft = await get_draft_brief(session, user.id)
        if not draft:
            await callback.answer("Бриф не найден", show_alert=True)
            return
        if draft.status == BriefRequestStatus.SUBMITTED.value and draft.admin_notified:
            await callback.message.answer(
                BRIEF_SUCCESS_TEXT.format(request_id=draft.request_code),
                reply_markup=brief_success_keyboard(),
            )
            await callback.answer()
            return

        if draft.is_trial and draft.inn and not draft.inn_manual_review:
            check = await check_trial_inn(session, user, draft.inn)
            if not check.ok:
                await _trial_block_message(callback.message, check.reason or "")
                await callback.answer()
                return

        try:
            draft = await submit_brief(session, draft)
            from services.admin_notify_service import notify_admin_brief

            notified = await notify_admin_brief(user, draft)
            draft.admin_notified = notified
            if not notified:
                draft.status = BriefRequestStatus.NOTIFY_FAILED.value
            await session.commit()
        except Exception:
            logger.exception("Brief submit failed user=%s", user.id)
            draft.status = BriefRequestStatus.NOTIFY_FAILED.value
            await session.commit()
            await callback.message.answer(BRIEF_FAILED_TEXT, reply_markup=brief_failed_keyboard())
            await callback.answer()
            return

    await state.clear()
    if draft.status == BriefRequestStatus.NOTIFY_FAILED.value:
        await callback.message.answer(BRIEF_FAILED_TEXT, reply_markup=brief_failed_keyboard())
    else:
        await callback.message.answer(
            BRIEF_SUCCESS_TEXT.format(request_id=draft.request_code),
            reply_markup=brief_success_keyboard(),
        )
    await callback.answer()


@router.message(F.text)
async def brief_recover_from_draft(message: Message, state: FSMContext) -> None:
    if await state.get_state():
        return

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        draft = await get_draft_brief(session, user.id)
        if not draft:
            return
        step = infer_brief_step(draft)

    if step == "business":
        await state.set_state(BriefState.business)
        await brief_business(message, state)
    elif step == "sales":
        await state.set_state(BriefState.sales)
        await message.answer(BRIEF_Q2_TEXT, reply_markup=brief_sales_keyboard())
    elif step == "competitors":
        await state.set_state(BriefState.competitors)
        await brief_competitors(message, state)
    elif step == "inn":
        await state.set_state(BriefState.inn)
        await _process_inn_input(message, state)
    elif step == "inn_manual":
        await state.set_state(BriefState.inn_manual)
        await brief_inn_manual_details(message, state)
    elif step == "ready":
        await _show_summary(message, state, message.from_user.id)

