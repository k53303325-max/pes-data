from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from database.database import async_session
from handlers.project import ProjectNameState
from keyboards.tariff_keyboard import CB_CREATE_ORDER, purchase_confirm_keyboard
from payments.yookassa import confirm_mock_payment, create_payment
from services.messages import BOT_SYSTEM_ERROR_ALERT
from services.pricing_service import format_purchase_confirm_text, quote_for_quantity
from services.project_service import PROJECT_NAME_PROMPT
from services.order_service import payment_success_text
from services.tariff_service import get_tariff
from services.telegram_notify import notify_payment_success
from services.user_service import get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


async def send_payment_success_message(
    target,
    order,
    state: FSMContext | None = None,
    *,
    edit: bool = False,
    telegram_id: int | None = None,
    user_db_id: int | None = None,
) -> None:
    text = payment_success_text(order.contact_limit)
    text += f"\n\n{PROJECT_NAME_PROMPT}"
    if edit:
        await target.edit_text(text)
    else:
        await target.answer(text)
    uid = user_db_id
    if state and uid:
        await state.set_state(ProjectNameState.waiting)


@router.callback_query(F.data.startswith(CB_CREATE_ORDER))
async def cb_create_order(callback: CallbackQuery, state: FSMContext) -> None:
    tariff_id = int(callback.data.removeprefix(CB_CREATE_ORDER))
    data = await state.get_data()
    contact_limit = data.get("contact_limit")
    amount = data.get("amount")

    if not contact_limit or not amount:
        await callback.answer("Сначала укажите количество контактов", show_alert=True)
        return

    await callback.answer()

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("Нажмите /start")
            return

        tariff = await get_tariff(session, tariff_id)
        if not tariff:
            await callback.message.answer("Тариф недоступен")
            return

        try:
            link = await create_payment(
                session,
                user,
                tariff,
                amount=amount,
                contact_limit=contact_limit,
            )
        except ValueError as exc:
            await callback.message.answer(str(exc)[:200])
            return
        except Exception:
            logger.exception("Payment creation failed")
            from services.admin_notify_service import notify_admin_error

            await notify_admin_error(
                event="payment_creation",
                user_label=str(callback.from_user.id),
                error_message="create_order",
            )
            await callback.message.answer(BOT_SYSTEM_ERROR_ALERT)
            return

    quote = quote_for_quantity(contact_limit)
    await callback.message.edit_text(
        format_purchase_confirm_text(quote),
        reply_markup=purchase_confirm_keyboard(tariff_id, link),
    )


async def handle_payment_success_callback(
    callback: CallbackQuery, payment_db_id: int, state: FSMContext
) -> None:
    from payments.yookassa import mock_payment_allowed

    if not mock_payment_allowed():
        await callback.answer("Тестовая оплата отключена", show_alert=True)
        return

    async with async_session() as session:
        result = await confirm_mock_payment(session, payment_db_id)
    if not result:
        await callback.answer("Платёж не найден или уже обработан", show_alert=True)
        return

    user, order = result
    await notify_payment_success(user.telegram_id, order.contact_limit)
    await send_payment_success_message(
        callback.message,
        order,
        state,
        edit=True,
        user_db_id=user.id,
    )
    await callback.answer("Пакет активирован")
