from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import CallbackQuery

from database.database import async_session
from keyboards.menu_keyboard import CB_MAIN_REFERRAL
from keyboards.referral_keyboard import (
    CB_REF_AGREE,
    CB_REF_CABINET,
    CB_REF_LINK,
    referral_link_keyboard,
    referral_program_keyboard,
)
from config.settings import settings
from services.referral_commission_service import get_partner_cabinet_stats, list_partner_commissions
from services.referral_service import ensure_user_referral_code, referral_link_for_user
from services.user_service import get_user_by_telegram_id

router = Router()


def _hold_days_label() -> str:
    d = settings.referral_payout_hold_days
    return f"{d} {_days_word(d)}"


def _days_word(n: int) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "дней"
    n = n % 10
    if n == 1:
        return "день"
    if 2 <= n <= 4:
        return "дня"
    return "дней"


def referral_program_text() -> str:
    hold = _hold_days_label()
    return f"""<b>Приведи клиента · получи 10%</b> 🐾

Знаешь бизнес, которому нужны контакты для продаж? Бери след 🐾

Приведи клиента и получай <b>10% от всех его покупок навсегда</b>.

Зарегистрируйся в партнёрской программе, получи личную ссылку и отправь её знакомому. Начисления и статус выплат смотри в кабинете партнёра.

<b>Условия:</b>
• бесплатный триал не участвует;
• процент считается от фактически оплаченной суммы (со скидкой);
• выплаты — раз в месяц, не раньше чем через {hold} после оплаты клиента;
• автоматический перевод денег на карту не обещаем — способ выплат согласуем с командой."""


def terms_before_link() -> str:
    hold = _hold_days_label()
    return (
        "Нажимая «Получить партнёрскую ссылку», вы принимаете условия программы: "
        "10% с каждой оплаченной покупки приведённого клиента, без триала, "
        f"с учётом возвратов и с задержкой выплат {hold}."
    )


def _fmt_rub(value: int) -> str:
    return f"{value:,} ₽".replace(",", " ")


@router.callback_query(F.data == CB_MAIN_REFERRAL)
async def cb_referral_program(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        show_agree = not (user and user.partner_agreed_at)
    await callback.message.edit_text(
        referral_program_text(),
        reply_markup=referral_program_keyboard(show_agree=show_agree),
    )
    await callback.answer()


@router.callback_query(F.data == CB_REF_AGREE)
async def cb_referral_agree(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        if not user.partner_agreed_at:
            user.partner_agreed_at = datetime.now(timezone.utc)
            await session.commit()
        await ensure_user_referral_code(session, user)
        link = referral_link_for_user(user.id)

    text = (
        f"{terms_before_link()}\n\n"
        f"<b>Ваша партнёрская ссылка:</b>\n{link}"
    )
    await callback.message.edit_text(text, reply_markup=referral_link_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_REF_LINK)
async def cb_referral_link(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        if not user.partner_agreed_at:
            await callback.answer("Сначала примите условия", show_alert=True)
            return
        await ensure_user_referral_code(session, user)
        link = referral_link_for_user(user.id)

    await callback.message.edit_text(
        f"<b>Ваша партнёрская ссылка:</b>\n{link}",
        reply_markup=referral_link_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == CB_REF_CABINET)
async def cb_referral_cabinet(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        stats = await get_partner_cabinet_stats(session, user.id)
        rows = await list_partner_commissions(session, user.id, limit=8)

    lines = [
        "<b>Кабинет партнёра</b>",
        "",
        f"Привели по ссылке: {stats.invited}",
        f"Клиентов с оплатами: {stats.paying_clients}",
        "",
        f"Всего начислено: {_fmt_rub(stats.total_commission)}",
        f"Ожидает {_hold_days_label()}: {_fmt_rub(stats.pending_commission)}",
        f"К выплате: {_fmt_rub(stats.eligible_commission)}",
        f"Уже выплачено: {_fmt_rub(stats.paid_out_commission)}",
        "",
        "<b>Последние начисления:</b>",
    ]
    if not rows:
        lines.append("— пока нет")
    else:
        for r in rows:
            lines.append(
                f"• {_fmt_rub(r.commission_amount)} ({r.status}) "
                f"от {_fmt_rub(r.paid_amount)} · {r.created_at.strftime('%d.%m.%Y')}"
            )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=referral_program_keyboard(show_agree=not user.partner_agreed_at),
    )
    await callback.answer()
