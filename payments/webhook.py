import json

from aiohttp import web
from aiogram import Bot

from config.settings import settings
from db.database import async_session
from payments.yookassa import process_successful_payment
from utils.logger import get_logger

logger = get_logger(__name__)


async def yookassa_webhook_handler(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]

    try:
        body = await request.json()
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in YooKassa webhook")
        return web.Response(status=400, text="Invalid JSON")

    event = body.get("event")
    obj = body.get("object", {})
    payment_id = obj.get("id")
    status = obj.get("status")

    logger.info("YooKassa webhook: event=%s payment_id=%s status=%s", event, payment_id, status)

    if event != "payment.succeeded" or status != "succeeded" or not payment_id:
        return web.Response(status=200, text="OK")

    async with async_session() as session:
        user = await process_successful_payment(session, payment_id)

    if user:
        try:
            await bot.send_message(
                user.user_id,
                f"✅ Оплата прошла успешно!\n\n"
                f"Ваш пакет активирован.\n"
                f"Лимит: {user.limit:,} контактов\n"
                f"Использовано: 0\n\n"
                f"Отправьте /add чтобы загрузить номера.".replace(",", " "),
            )
        except Exception as exc:
            logger.error("Failed to notify user %s: %s", user.user_id, exc)

    return web.Response(status=200, text="OK")


def create_webhook_app(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post(settings.yookassa_webhook_path, yookassa_webhook_handler)
    app.router.add_get("/health", lambda _: web.Response(text="OK"))
    return app
