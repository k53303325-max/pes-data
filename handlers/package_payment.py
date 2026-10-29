from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from database.database import async_session
from keyboards.package_payment_keyboard import (
    CB_PAY_PKG_PREFIX,
    package_payment_keyboard,
)
from services.messages import BOT_SYSTEM_ERROR_ALERT
from services.package_payment import (
    create_package_yookassa_payment,
    format_payment_intro,
    resolve_package,
)
from services.user_service import get_active_order, get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


@router.callback_query(F.data.startswith(CB_PAY_PKG_PREFIX))
async def cb_pay_package(callback: CallbackQuery) -> None:
    code = callback.data.removeprefix(CB_PAY_PKG_PREFIX)
    try:
        pkg = resolve_package(code)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.answer()

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("Нажмите /start")
            return
        if await get_active_order(session, user.id):
            await callback.message.answer("Сначала завершите текущий пакет")
            return
        try:
            from services.bank_payment_service import cancel_user_pending_payments

            await cancel_user_pending_payments(session, user.id)
            link = await create_package_yookassa_payment(session, user, pkg)
        except ValueError as exc:
            await callback.message.answer(str(exc)[:200])
            return
        except Exception:
            logger.exception("Package payment failed code=%s", code)
            from services.admin_notify_service import notify_admin_error

            await notify_admin_error(
                event="package_payment",
                user_label=str(callback.from_user.id),
                error_message=code,
            )
            await callback.message.answer(BOT_SYSTEM_ERROR_ALERT)
            return

    await callback.message.edit_text(
        format_payment_intro(pkg),
        reply_markup=package_payment_keyboard(link, code),
    )
