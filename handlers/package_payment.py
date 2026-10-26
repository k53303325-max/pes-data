from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from database.database import async_session
from keyboards.package_payment_keyboard import (
    CB_BANK_PKG_PREFIX,
    CB_PAY_PKG_PREFIX,
    package_payment_keyboard,
)
from services.messages import BOT_SYSTEM_ERROR_ALERT, BOT_SYSTEM_ERROR_TEXT
from services.package_payment import (
    create_bank_payment_request,
    create_package_yookassa_payment,
    format_payment_intro,
    resolve_package,
)
from services.user_service import get_active_order, get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

BANK_PAYMENT_USER_TEXT = (
    "🏦 <b>Запрос на оплату с расчётного счёта</b>\n\n"
    "Команда подготовит счёт и пришлёт реквизиты здесь, в Telegram.\n\n"
    "Номер заявки: <b>#{request_id}</b>\n\n"
    "Если нужно срочно — нажмите «Связаться с командой» в главном меню."
)


@router.callback_query(F.data.startswith(CB_PAY_PKG_PREFIX))
async def cb_pay_package(callback: CallbackQuery) -> None:
    code = callback.data.removeprefix(CB_PAY_PKG_PREFIX)
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
        try:
            link = await create_package_yookassa_payment(session, user, pkg)
        except ValueError as exc:
            await callback.answer(str(exc)[:200], show_alert=True)
            return
        except Exception:
            logger.exception("Package payment failed code=%s", code)
            from services.admin_notify_service import notify_admin_error

            await notify_admin_error(
                event="package_payment",
                user_label=str(callback.from_user.id),
                error_message=code,
            )
            await callback.answer(BOT_SYSTEM_ERROR_ALERT, show_alert=True)
            return

    await callback.message.edit_text(
        format_payment_intro(pkg),
        reply_markup=package_payment_keyboard(link, code),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_BANK_PKG_PREFIX))
async def cb_bank_package(callback: CallbackQuery) -> None:
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
        try:
            request = await create_bank_payment_request(session, user, pkg)
        except Exception:
            logger.exception("Bank payment request failed")
            await callback.answer(BOT_SYSTEM_ERROR_ALERT, show_alert=True)
            return

        from services.admin_notify_service import notify_admin_bank_payment

        await notify_admin_bank_payment(user, request, pkg)

    await callback.message.edit_text(
        BANK_PAYMENT_USER_TEXT.format(request_id=request.id),
    )
    await callback.answer("Заявка отправлена")
