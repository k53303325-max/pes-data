from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from handlers.orders import handle_payment_success_callback, send_payment_success_message
from keyboards.payment_keyboard import CB_MOCK_PAY_PREFIX, CB_PROMO_PKG_PREFIX, CB_PROMO_PREFIX
from services.package_catalog import get_package
from services.package_payment import resolve_package
from keyboards.start_keyboard import CB_BACK, back_keyboard
from services.messages import BOT_SYSTEM_ERROR_TEXT
from services.promo_service import activate_promo_package, verify_test_promo
from services.tariff_service import get_tariff
from services.telegram_notify import notify_payment_success
from services.user_service import get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


class PromoState(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data.startswith(CB_PROMO_PKG_PREFIX))
async def cb_promo_package(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.removeprefix(CB_PROMO_PKG_PREFIX)
    try:
        pkg = resolve_package(code)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await state.set_state(PromoState.waiting_code)
    await state.update_data(
        package_code=code,
        tariff_id=pkg.tariff_id,
        contact_limit=pkg.contact_count,
        amount=pkg.price,
    )
    await callback.message.edit_text(
        "🎟 <b>Промокод</b>\n\n"
        "Введите промокод одним сообщением.\n"
        f"Пакет: <b>{pkg.name}</b> · {pkg.contact_count} контактов",
        reply_markup=back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PROMO_PREFIX))
async def cb_promo_tariff(callback: CallbackQuery, state: FSMContext) -> None:
    tariff_id = int(callback.data.removeprefix(CB_PROMO_PREFIX))
    await state.set_state(PromoState.waiting_code)
    await state.update_data(tariff_id=tariff_id)
    await callback.message.edit_text(
        "🎟 <b>Промокод</b>\n\nВведите промокод одним сообщением:",
        reply_markup=back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_MOCK_PAY_PREFIX))
async def cb_mock_pay(callback: CallbackQuery, state: FSMContext) -> None:
    from payments.yookassa import mock_payment_allowed

    if not mock_payment_allowed():
        await callback.answer("Тестовая оплата отключена", show_alert=True)
        return

    payment_id = int(callback.data.removeprefix(CB_MOCK_PAY_PREFIX))
    await handle_payment_success_callback(callback, payment_id, state)


@router.callback_query(F.data == CB_BACK, PromoState.waiting_code)
async def cb_promo_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Ввод промокода отменён.\n\nНажмите /start или выберите пакет снова.",
        reply_markup=back_keyboard(),
    )
    await callback.answer()


@router.message(PromoState.waiting_code, F.text)
async def process_promo_code(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tariff_id = data.get("tariff_id")
    if not tariff_id:
        await state.clear()
        await message.answer("⚠️ Сессия истекла. Нажмите /start")
        return

    if not verify_test_promo(message.text or ""):
        await message.answer("❌ Неверный промокод. Попробуйте ещё раз или нажмите «Назад».")
        return

    contact_limit = data.get("contact_limit")
    package_code = data.get("package_code")
    if package_code and not contact_limit:
        pkg = get_package(package_code)
        if pkg and pkg.tariff_id:
            contact_limit = pkg.contact_count
            data["tariff_id"] = pkg.tariff_id
            data["contact_limit"] = contact_limit
    if not contact_limit:
        await message.answer("Выберите пакет в «Пакеты и цены» и нажмите «Промокод».")
        return

    await state.clear()

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        tariff = await get_tariff(session, tariff_id)
        if not user or not tariff:
            await message.answer(BOT_SYSTEM_ERROR_TEXT)
            return
        try:
            user, order = await activate_promo_package(
                session,
                user,
                tariff,
                contact_limit=contact_limit,
            )
        except ValueError as exc:
            await message.answer(f"❌ {exc}")
            return
        except Exception as exc:
            logger.exception("Promo activation failed")
            from services.admin_notify_service import notify_admin_error

            await notify_admin_error(
                event="promo_activation",
                user_label=str(message.from_user.id),
                error_message=str(exc),
            )
            await message.answer(BOT_SYSTEM_ERROR_TEXT)
            return

    await notify_payment_success(user.telegram_id, order.contact_limit)
    await send_payment_success_message(
        message,
        order,
        state,
        user_db_id=user.id,
    )


