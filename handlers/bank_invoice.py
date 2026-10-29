from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from keyboards.menu_keyboard import CB_MAIN_MENU
from keyboards.package_payment_keyboard import CB_BANK_PKG_PREFIX
from keyboards.start_keyboard import back_keyboard
from services.bank_payment_service import create_bank_invoice_request, parse_invoice_message
from services.messages import BOT_SYSTEM_ERROR_TEXT
from services.package_payment import resolve_package
from services.user_service import get_active_order, get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

INVOICE_PROMPT = (
    "🏦 <b>Счёт на оплату</b>\n\n"
    "Пришлите <b>название компании или ИП</b>, <b>ИНН</b> и <b>email</b> для счёта.\n"
    "Если есть карточка с реквизитами — отправьте её файлом в следующем сообщении "
    "(можно вместе с текстом).\n\n"
    "Пакет: <b>{package_name}</b> · {amount} ₽"
)

INVOICE_SUCCESS = (
    "✅ Запрос принят.\n\n"
    "Номер обращения: <b>#{request_id}</b>\n\n"
    "Команда проверит пакет и выставит счёт. До поступления денег на счёт заказ "
    "в статусе «ожидает оплаты». Скриншот платёжки сам по себе не запускает выдачу."
)


class BankInvoiceState(StatesGroup):
    waiting = State()


@router.callback_query(F.data.startswith(CB_BANK_PKG_PREFIX))
async def cb_bank_invoice_start(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.removeprefix(CB_BANK_PKG_PREFIX)
    try:
        pkg = resolve_package(code)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        if await get_active_order(session, user.id):
            await callback.answer("Сначала завершите текущий пакет", show_alert=True)
            return

    amount = f"{pkg.price:,} ₽".replace(",", " ")
    await state.set_state(BankInvoiceState.waiting)
    await state.update_data(package_code=code)
    await callback.message.edit_text(
        INVOICE_PROMPT.format(package_name=pkg.name, amount=amount),
        reply_markup=back_keyboard(),
    )
    await callback.answer()


@router.message(BankInvoiceState.waiting, F.text | F.document)
async def bank_invoice_receive(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    code = data.get("package_code")
    if not code:
        await state.clear()
        await message.answer("Сессия истекла. Выберите пакет снова.")
        return

    try:
        pkg = resolve_package(code)
    except ValueError:
        await state.clear()
        await message.answer(BOT_SYSTEM_ERROR_TEXT)
        return

    file_id = None
    file_name = None
    text = message.text or message.caption or ""
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name

    if not text.strip() and not file_id:
        await message.answer("Пришлите текст с названием, ИНН и email или файл с реквизитами.")
        return

    try:
        company, inn, email = parse_invoice_message(text)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    row = None
    try:
        async with async_session() as session:
            user = await get_user_by_telegram_id(session, message.from_user.id)
            if not user:
                await message.answer(BOT_SYSTEM_ERROR_TEXT)
                return
            row = await create_bank_invoice_request(
                session,
                user,
                pkg,
                company_name=company,
                company_inn=inn,
                invoice_email=email,
                requisites_file_id=file_id,
                requisites_file_name=file_name,
            )
            from services.admin_notify_service import notify_admin_bank_payment

            await notify_admin_bank_payment(user, row, pkg)
    except Exception:
        logger.exception("bank invoice create failed")
        await message.answer(BOT_SYSTEM_ERROR_TEXT)
        return

    await state.clear()
    await message.answer(INVOICE_SUCCESS.format(request_id=row.id))
