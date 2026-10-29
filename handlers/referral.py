from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from database.database import async_session
from keyboards.menu_keyboard import CB_MAIN_REFERRAL, back_to_main_keyboard
from services.referral_service import ensure_user_referral_code, get_referral_stats, referral_link_for_user
from services.user_service import get_user_by_telegram_id

router = Router()

REFERRAL_INTRO = """<b>Партнёрская программа</b> 🤝

Поделитесь ссылкой с коллегой или партнёром. Если он зарегистрируется в боте и оплатит пакет, мы зафиксируем это за вами.

<b>Условия бонуса</b> (скидка, дополнительные контакты или вознаграждение) согласуются с командой — напишите нам, когда увидите первую оплату.

<b>Ваша ссылка:</b>
{link}

<b>Статистика:</b>
• перешли по ссылке: {invited}
• отправили бриф: {briefs}
• оплатили пакет: {paid}"""


@router.callback_query(F.data == CB_MAIN_REFERRAL)
async def cb_referral(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return
        await ensure_user_referral_code(session, user)
        link = referral_link_for_user(user.id)
        stats = await get_referral_stats(session, user.id)

    text = REFERRAL_INTRO.format(
        link=link,
        invited=stats.invited,
        briefs=stats.briefs_submitted,
        paid=stats.paid,
    )
    await callback.message.edit_text(text, reply_markup=back_to_main_keyboard())
    await callback.answer()
