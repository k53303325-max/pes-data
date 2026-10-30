from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.middleware.sessions import SessionMiddleware

from admin_web.auth import check_credentials, get_admin_username, is_authenticated, login, logout
from bot.factory import ensure_telegram_webhook, get_bot, get_dispatcher
from config.settings import settings
from database.database import async_session, init_db
from database.models import (
    BankPaymentRequest,
    BankPaymentStatus,
    Delivery,
    DeliveryType,
    NicheBriefRequest,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Project,
    Tariff,
    TrialEntitlement,
    User,
    UserStatus,
)
from services.admin_orders_service import format_purchase_date, list_active_orders
from services.admin_delivery_service import delivery_type_label, list_delivery_history
from services.admin_notify_service import (
    get_or_create_default_config,
    notify_admin_daily_report,
    update_notification_config,
)
from services.activity_service import format_activity_line, get_recent_activities
from services.chat_log_service import (
    count_user_chat_messages,
    format_chat_preview,
    get_user_chat_messages,
    list_recent_chats,
    strip_html,
)
from services.project_service import (
    delete_project,
    format_project_price,
    get_order_price,
    get_project_by_order,
    get_project_detail,
    list_projects,
)
from services.admin_stats_service import (
    dashboard_stats,
    list_users,
    sales_by_day,
    summarize_user_payments,
)
from services.admin_tariff_service import list_all_tariffs_admin, save_tariff, toggle_tariff_active
from services.brief_admin_service import (
    BANK_STATUS_LABELS,
    BRIEF_STATUS_LABELS,
    TRIAL_STATUS_LABELS,
    format_sales_team,
    get_brief,
    list_bank_payments,
    list_briefs,
    list_trials,
    get_bank_payment,
    update_bank_payment_status,
    update_trial_status,
)
from services.brief_service import phones_from_storage
from services.package_catalog import PACKAGES
from services.promo_service import promo_hash_hint
from services.referral_service import get_referral_stats, referral_code_for_user, referral_link_for_user
from services.delivery_service import (
    commit_delivery,
    parse_contacts_file,
    parse_contacts_text,
    phones_to_text,
    preview_delivery,
)
from services.order_service import create_test_order, payment_success_text
from services.telegram_notify import (
    deliver_contacts_to_user,
    notify_package_completed,
    notify_payment_success,
)
from payments.yookassa import (
    process_successful_payment,
    sync_all_pending_payments,
    sync_pending_payment,
)
from services.user_service import get_user_with_orders, order_remaining, delete_user
from utils.logger import get_logger
from utils.phone import normalize_phone

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
logger = get_logger(__name__)


def render(request: Request, name: str, context: dict | None = None):
    return templates.TemplateResponse(request, name, context or {})

_db_initialized = False
_polling_task: asyncio.Task | None = None


@asynccontextmanager
async def _app_lifespan(_application: FastAPI):
    from services.admin_notify_service import ensure_admin_notify_config
    global _polling_task

    try:
        await _ensure_db()
        await ensure_admin_notify_config()
    except Exception:
        logger.exception("Startup init_db failed")
    if settings.telegram_bot_enabled:
        if settings.telegram_polling:
            from bot.polling_runner import run_telegram_polling

            _polling_task = asyncio.create_task(run_telegram_polling())
        elif settings.use_webhook:
            asyncio.create_task(_setup_telegram_webhook_once())
    yield
    if _polling_task and not _polling_task.done():
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Пёс Дата Admin", lifespan=_app_lifespan)


async def _ensure_db() -> None:
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True


async def _setup_telegram_webhook_once() -> None:
    try:
        import asyncio

        await asyncio.wait_for(ensure_telegram_webhook(), timeout=25.0)
    except Exception:
        logger.exception("Telegram webhook setup failed (non-fatal)")


DB_SETUP_HTML = """
<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>Пёс Дата — настройка</title>
<style>body{font-family:system-ui;max-width:560px;margin:60px auto;padding:0 20px;background:#1E1E3A;color:#F4F4FC}
h1{color:#5B5FC7}ol{line-height:1.8}a{color:#7B7FE0}code{background:#ffffff15;padding:2px 6px;border-radius:4px}</style></head>
<body>
<h1>🐶 Пёс Дата</h1>
<p>Остался один шаг — подключить базу данных прямо в Vercel (без neon.tech):</p>
<ol>
<li>Откройте <a href="https://vercel.com/kates-projects-ad4765fe/pes-data/stores">Storage проекта pes-data</a></li>
<li><strong>Create Database</strong> → <strong>Postgres</strong> → <strong>Continue</strong></li>
<li>Выберите регион → <strong>Create</strong> → <strong>Connect to pes-data</strong></li>
<li>Нажмите <strong>Redeploy</strong> в <a href="https://vercel.com/kates-projects-ad4765fe/pes-data/deployments">Deployments</a></li>
</ol>
<p>Или из терминала: <code>./scripts/setup_vercel_postgres.sh</code></p>
<p>После этого откройте <a href="/login">/login</a> — появится админка.</p>
<p>Telegram-бот подключится автоматически через webhook.</p>
</body></html>
"""


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.admin_secret_key,
    session_cookie="pes_admin_session",
    max_age=86400 * 7,
    same_site="lax",
    https_only=settings.is_vercel or settings.is_onreza,
)

static_dir = BASE / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

STATUS_LABELS = {
    "new": "Новый",
    "active": "Активен",
    "finished": "Завершён",
    "blocked": "Заблокирован",
    "pending": "Ожидает оплаты",
    "paid": "Оплачено",
    "canceled": "Отменено",
    "created": "Создан",
    "in_progress": "Выполняется",
    "completed": "Завершён",
    "disabled": "Отключён",
    "deleted": "Удалён",
}


@app.middleware("http")
async def init_db_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/webhook/telegram"):
        if request.url.path == "/webhook/telegram" and not _db_initialized:
            try:
                await asyncio.wait_for(_ensure_db(), timeout=10.0)
            except Exception as exc:
                logger.error("init_db for webhook failed: %s", exc)
        return await call_next(request)
    if settings.is_vercel and not settings.database_url:
        if request.url.path in ("/webhook/telegram", settings.yookassa_webhook_path):
            return HTMLResponse('{"ok":false,"error":"no db"}', status_code=503)
        return HTMLResponse(DB_SETUP_HTML, status_code=503)
    try:
        import asyncio

        await asyncio.wait_for(_ensure_db(), timeout=20.0)
    except asyncio.TimeoutError:
        logger.error("init_db timeout path=%s", request.url.path)
        return HTMLResponse(
            "<h1>База данных не отвечает</h1><p>Попробуйте через минуту.</p>",
            status_code=503,
        )
    except Exception as exc:
        return HTMLResponse(
            f"<h1>Ошибка подключения к БД</h1><pre>{exc}</pre>"
            "<p>Vercel → Storage → Postgres → Connect → Redeploy</p>",
            status_code=503,
        )
    return await call_next(request)


@app.get("/health")
async def health(deep: bool = False):
    platform = "onreza" if settings.is_onreza else ("vercel" if settings.is_vercel else "local")
    payload: dict = {
        "ok": True,
        "platform": platform,
        "app_url": settings.app_url,
        "telegram_mode": (
            "off"
            if not settings.telegram_bot_enabled
            else ("polling" if settings.telegram_polling else "webhook")
        ),
        "db_ready": _db_initialized,
    }
    if deep and settings.bot_token and not settings.telegram_polling:
        try:
            bot = get_bot()
            info = await asyncio.wait_for(bot.get_webhook_info(), timeout=5.0)
            payload["telegram_webhook"] = info.url
            payload["telegram_pending"] = info.pending_update_count
            if info.last_error_message:
                payload["telegram_last_error"] = info.last_error_message[:200]
        except Exception as exc:
            payload["telegram_webhook_error"] = str(exc)[:200]
    return payload


async def _process_telegram_update(data: dict) -> None:
    from aiogram.types import Update

    try:
        bot = get_bot()
        dp = get_dispatcher()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception:
        logger.exception("Telegram update processing failed")


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Telegram Bot webhook — быстрый 200 OK, обработка в фоне."""
    if settings.telegram_polling:
        return {"ok": True}
    if not settings.bot_token:
        return {"ok": False, "error": "BOT_TOKEN not set"}

    try:
        data = await request.json()
    except Exception:
        logger.warning("Telegram webhook: invalid JSON")
        return {"ok": True}

    background_tasks.add_task(_process_telegram_update, data)
    return {"ok": True}


@app.post(settings.yookassa_webhook_path)
async def yookassa_webhook(request: Request):
    """Webhook ЮKassa — подтверждение оплаты."""
    try:
        body = await request.json()
    except Exception:
        logger.warning("YooKassa webhook: invalid JSON")
        return {"status": "invalid json"}

    event = body.get("event")
    obj = body.get("object", {})
    payment_id = obj.get("id")
    status = obj.get("status")
    logger.info(
        "YooKassa webhook: event=%s status=%s payment_id=%s",
        event,
        status,
        payment_id,
    )

    if event != "payment.succeeded" or status != "succeeded" or not payment_id:
        return {"status": "ignored"}

    try:
        async with async_session() as session:
            result = await process_successful_payment(session, payment_id)
    except Exception:
        logger.exception("YooKassa webhook failed payment_id=%s", payment_id)
        return HTMLResponse('{"status":"error"}', status_code=500)

    if result:
        user, order = result
        await notify_payment_success(user.telegram_id, order.contact_limit)
    else:
        logger.warning(
            "YooKassa webhook: activation returned None payment_id=%s",
            payment_id,
        )

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {
        "status": "ok" if settings.database_url else "need_database",
        "vercel": settings.is_vercel,
        "app_url": settings.app_url,
    }


def auth_guard(request: Request) -> RedirectResponse | None:
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=303)
    return None


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", {"error": None})


@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if check_credentials(username, password):
        login(request, username)
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", {"error": "Неверный логин или пароль"})


@app.get("/logout")
async def logout_view(request: Request):
    logout(request)
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        stats = await dashboard_stats(session)
        recent_activities = await get_recent_activities(session, limit=12)
    return render(
        request,
        "dashboard.html",
        {
            "stats": stats,
            "labels": STATUS_LABELS,
            "recent_activities": recent_activities,
            "format_activity_line": format_activity_line,
        },
    )


@app.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    q: str = "",
    status: str = "",
    pay_filter: str = "",
    msg: str = "",
):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        users = await list_users(session, q, status, pay_filter)
    return render(
        request,
        "users.html",
        {
            "users": users,
            "q": q,
            "status": status,
            "pay_filter": pay_filter,
            "labels": STATUS_LABELS,
            "msg": msg,
            "summarize_user_payments": summarize_user_payments,
        },
    )


@app.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        user = await get_user_with_orders(session, user_id)
        if not user:
            return RedirectResponse("/users", status_code=303)
        deliveries = (
            await session.execute(
                select(Delivery)
                .where(Delivery.user_id == user_id)
                .order_by(Delivery.created_at.desc())
            )
        ).scalars().all()
        projects = sorted(user.projects, key=lambda p: p.created_at, reverse=True)
        payments = sorted(user.payments, key=lambda p: p.created_at, reverse=True)
        project_prices = {}
        for project in projects:
            if project.order:
                project_prices[project.id] = await get_order_price(session, project.order)
    return render(
        request,
        "user_detail.html",
        {
            "user": user,
            "projects": projects,
            "payments": payments,
            "project_prices": project_prices,
            "deliveries": deliveries,
            "labels": STATUS_LABELS,
            "order_remaining": order_remaining,
            "format_project_price": format_project_price,
            "msg": msg,
            "summarize_user_payments": summarize_user_payments,
        },
    )


@app.get("/chats", response_class=HTMLResponse)
async def chats_page(request: Request, q: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        chats = await list_recent_chats(session, limit=100)
        if q:
            q_clean = q.strip().lstrip("@").lower()
            chats = [
                c
                for c in chats
                if q_clean in str(c["user"].telegram_id)
                or (c["user"].username and q_clean in c["user"].username.lower())
                or (c["user"].first_name and q_clean in c["user"].first_name.lower())
            ]
    return render(
        request,
        "chats.html",
        {"chats": chats, "q": q, "labels": STATUS_LABELS},
    )


@app.get("/users/{user_id}/chat", response_class=HTMLResponse)
async def user_chat_page(request: Request, user_id: int, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        user = await get_user_with_orders(session, user_id)
        if not user:
            return RedirectResponse("/chats", status_code=303)
        total = await count_user_chat_messages(session, user_id)
        messages = await get_user_chat_messages(session, user_id, limit=2000)
    return render(
        request,
        "user_chat.html",
        {
            "user": user,
            "messages": messages,
            "total": total,
            "labels": STATUS_LABELS,
            "strip_html": strip_html,
            "msg": msg,
        },
    )


@app.post("/users/{user_id}/chat/send")
async def user_chat_send(request: Request, user_id: int, text: str = Form(...)):
    if redirect := auth_guard(request):
        return redirect
    body = (text or "").strip()
    if not body:
        return RedirectResponse(
            f"/users/{user_id}/chat?msg={quote('Введите текст сообщения')}",
            status_code=303,
        )
    if len(body) > 4000:
        return RedirectResponse(
            f"/users/{user_id}/chat?msg={quote('Слишком длинное сообщение (макс. 4000 символов)')}",
            status_code=303,
        )
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return RedirectResponse("/users?msg=Пользователь не найден", status_code=303)
        result = await _send_user_telegram_message(
            session, user, body, source="admin.chat"
        )
    if not result.get("ok"):
        err = quote(result.get("error", "Не удалось отправить")[:200])
        return RedirectResponse(f"/users/{user_id}/chat?msg={err}", status_code=303)
    if result.get("queued"):
        note = "Сообщение в очереди — бот доставит в Telegram в течение нескольких секунд"
    else:
        note = "Сообщение отправлено в Telegram"
    return RedirectResponse(
        f"/users/{user_id}/chat?msg={quote(note)}",
        status_code=303,
    )


async def _send_user_telegram_message(
    session,
    user: User,
    text: str,
    *,
    source: str,
) -> dict:
    """ONREZA не ходит в api.telegram.org — очередь в БД, poller на Amvera отправляет."""
    if settings.is_onreza or settings.is_vercel:
        from services.telegram_outbox_service import enqueue_telegram_message

        await enqueue_telegram_message(session, user, text, source=source)
        return {"ok": True, "queued": True, "telegram_id": user.telegram_id}

    import aiohttp

    from services.chat_log_service import log_outgoing

    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    payload = {"chat_id": user.telegram_id, "text": text, "parse_mode": "HTML"}
    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(url, json=payload, timeout=20) as resp:
                body = await resp.json(content_type=None)
                if resp.status != 200 or not body.get("ok"):
                    return {"ok": False, "error": body.get("description", "telegram_error")}
    except Exception as exc:
        logger.exception("Telegram send failed user_id=%s", user.id)
        return {"ok": False, "error": str(exc)}

    await log_outgoing(
        session,
        telegram_id=user.telegram_id,
        content=text,
        message_type="text",
        source=source,
    )
    return {"ok": True, "telegram_id": user.telegram_id}


@app.post("/internal/notify-payment/{user_id}")
async def internal_notify_payment(user_id: int, secret: str = ""):
    """Разовая отправка уведомления об оплате (секрет ADMIN_SECRET_KEY)."""
    if not secret or secret != settings.admin_secret_key:
        return {"ok": False, "error": "forbidden"}
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return {"ok": False, "error": "user_not_found"}
        from services.user_service import get_active_order

        order = await get_active_order(session, user.id)
        if not order:
            return {"ok": False, "error": "no_active_order"}
        await session.refresh(order, ["tariff"])
        text = payment_success_text(order.contact_limit)
        return await _send_user_telegram_message(
            session, user, text, source="admin.manual_payment_notice"
        )


@app.post("/internal/send-message/{user_id}")
async def internal_send_message(request: Request, user_id: int, secret: str = ""):
    """Ручная отправка сообщения пользователю (секрет ADMIN_SECRET_KEY)."""
    if not secret or secret != settings.admin_secret_key:
        return {"ok": False, "error": "forbidden"}
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid json"}
    text = (body.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "empty text"}
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return {"ok": False, "error": "user_not_found"}
        return await _send_user_telegram_message(
            session, user, text, source="admin.manual_message"
        )


@app.post("/users/{user_id}/send-payment-notice")
async def user_send_payment_notice(request: Request, user_id: int):
    """Разовая ручная отправка уведомления об успешной оплате."""
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return RedirectResponse("/users?msg=Пользователь не найден", status_code=303)
        from services.user_service import get_active_order

        order = await get_active_order(session, user.id)
        if not order:
            return RedirectResponse(
                f"/users/{user_id}?msg=Нет активного пакета",
                status_code=303,
            )
        await session.refresh(order, ["tariff"])
        text = payment_success_text(order.contact_limit)
        ok = False
        import aiohttp

        url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
        payload = {"chat_id": user.telegram_id, "text": text, "parse_mode": "HTML"}
        try:
            async with aiohttp.ClientSession() as http:
                async with http.post(url, json=payload) as resp:
                    body = await resp.json(content_type=None)
                    ok = resp.status == 200 and body.get("ok")
        except Exception:
            logger.exception("Manual payment notice failed user_id=%s", user_id)
        if ok:
            from services.chat_log_service import log_outgoing

            await log_outgoing(
                session,
                telegram_id=user.telegram_id,
                content=text,
                message_type="text",
                source="admin.manual_payment_notice",
            )
            return RedirectResponse(
                f"/users/{user_id}?msg=Уведомление об оплате отправлено",
                status_code=303,
            )
    return RedirectResponse(
        f"/users/{user_id}?msg=Не удалось отправить сообщение в Telegram",
        status_code=303,
    )


@app.post("/users/{user_id}/delete")
async def user_delete(request: Request, user_id: int):
    if redirect := auth_guard(request):
        return redirect
    try:
        async with async_session() as session:
            deleted = await delete_user(session, user_id)
    except Exception:
        logger.exception("Delete user failed id=%s", user_id)
        return RedirectResponse(
            f"/users?msg={quote('Не удалось удалить пользователя. Попробуйте ещё раз.')}",
            status_code=303,
        )
    if not deleted:
        return RedirectResponse(f"/users?msg={quote('Пользователь не найден')}", status_code=303)
    return RedirectResponse(f"/users?msg={quote('Пользователь удалён')}", status_code=303)


@app.post("/users/{user_id}/projects/{project_id}/delete")
async def user_project_delete(request: Request, user_id: int, project_id: int):
    if redirect := auth_guard(request):
        return redirect
    try:
        async with async_session() as session:
            project = await session.get(Project, project_id)
            if not project or project.user_id != user_id:
                return RedirectResponse(
                    f"/users/{user_id}?msg={quote('Проект не найден')}",
                    status_code=303,
                )
            deleted = await delete_project(session, project_id)
    except Exception:
        logger.exception("Delete project failed user_id=%s project_id=%s", user_id, project_id)
        return RedirectResponse(
            f"/users/{user_id}?msg={quote('Не удалось удалить проект')}",
            status_code=303,
        )
    if not deleted:
        return RedirectResponse(
            f"/users/{user_id}?msg={quote('Проект не найден')}",
            status_code=303,
        )
    return RedirectResponse(
        f"/users/{user_id}?msg={quote('Проект удалён')}",
        status_code=303,
    )


@app.get("/packages", response_class=HTMLResponse)
async def packages_admin_page(request: Request):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        tariffs = await list_all_tariffs_admin(session)
    catalog = [
        {
            "code": p.code,
            "name": p.name,
            "contact_count": p.contact_count,
            "price": p.price,
            "tariff_id": p.tariff_id,
        }
        for p in PACKAGES
    ]
    return render(request, "packages.html", {"catalog": catalog, "tariffs": tariffs})


@app.get("/tariffs", response_class=HTMLResponse)
async def tariffs_page_redirect(request: Request):
    if redirect := auth_guard(request):
        return redirect
    return RedirectResponse("/packages", status_code=303)


@app.get("/briefs", response_class=HTMLResponse)
async def briefs_page(request: Request, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        briefs = await list_briefs(session)
    return render(
        request,
        "briefs.html",
        {
            "briefs": briefs,
            "brief_labels": BRIEF_STATUS_LABELS,
            "msg": msg,
            "promo_hint": promo_hash_hint(),
        },
    )


@app.get("/briefs/{brief_id}", response_class=HTMLResponse)
async def brief_detail_page(request: Request, brief_id: int, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        brief = await get_brief(session, brief_id)
        if not brief:
            return RedirectResponse("/briefs?msg=Обращение не найдено", status_code=303)
        trials = (
            await session.execute(
                select(TrialEntitlement).where(TrialEntitlement.user_id == brief.user_id)
            )
        ).scalars().all()
    competitors_text = brief.competitor_phones_raw or "—"
    if brief.competitors_need_help:
        competitors_text = "нужна помощь с выбором"
    elif brief.competitor_phones_normalized:
        competitors_text = "\n".join(phones_from_storage(brief.competitor_phones_normalized))
    return render(
        request,
        "brief_detail.html",
        {
            "brief": brief,
            "brief_labels": BRIEF_STATUS_LABELS,
            "trial_labels": TRIAL_STATUS_LABELS,
            "trials": trials,
            "sales_label": format_sales_team(brief.sales_team),
            "competitors_text": competitors_text,
            "msg": msg,
        },
    )


@app.get("/trials", response_class=HTMLResponse)
async def trials_page(request: Request, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        trials = await list_trials(session)
    return render(
        request,
        "trials.html",
        {"trials": trials, "trial_labels": TRIAL_STATUS_LABELS, "msg": msg},
    )


@app.post("/trials/{trial_id}/status")
async def trial_status_update(
    request: Request,
    trial_id: int,
    status: str = Form(...),
    next: str = Form(""),
):
    if redirect := auth_guard(request):
        return redirect
    try:
        async with async_session() as session:
            row = await update_trial_status(session, trial_id, status)
        msg = quote(f"Статус триала {row.inn} обновлён")
        if next.startswith("/"):
            sep = "&" if "?" in next else "?"
            dest = f"{next}{sep}msg={msg}"
        else:
            dest = f"/briefs?msg={msg}"
        return RedirectResponse(dest, status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/trials?msg={quote(str(exc))}", status_code=303)


@app.get("/referrals", response_class=HTMLResponse)
async def referrals_admin_page(request: Request):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        all_users = (await session.execute(select(User).order_by(User.id))).scalars().all()
        rows = []
        for u in all_users:
            stats = await get_referral_stats(session, u.id)
            if stats.invited <= 0 and not u.referred_by_user_id:
                continue
            code = u.referral_code or referral_code_for_user(u.id)
            rows.append({"user": u, "code": code, "stats": stats})
        rows.sort(key=lambda r: (r["stats"].paid, r["stats"].invited), reverse=True)
        recent = (
            await session.execute(
                select(User)
                .where(User.referred_by_user_id.isnot(None))
                .options(selectinload(User.referred_by))
                .order_by(User.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
    return render(
        request,
        "referrals.html",
        {
            "rows": rows[:100],
            "recent": recent,
            "bot_username": settings.bot_username,
        },
    )


@app.get("/bank-payments", response_class=HTMLResponse)
async def bank_payments_page(request: Request, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        requests_list = await list_bank_payments(session)
    return render(
        request,
        "bank_payments.html",
        {"requests": requests_list, "bank_labels": BANK_STATUS_LABELS, "msg": msg},
    )


@app.post("/bank-payments/{request_id}/status")
async def bank_payment_status_update(
    request: Request,
    request_id: int,
    status: str = Form(...),
    admin_note: str = Form(""),
):
    if redirect := auth_guard(request):
        return redirect
    try:
        async with async_session() as session:
            await update_bank_payment_status(
                session, request_id, status, admin_note=admin_note
            )
        return RedirectResponse("/bank-payments?msg=Статус сохранён", status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/bank-payments?msg={quote(str(exc))}", status_code=303)


def _default_bank_invoice_message(row: BankPaymentRequest) -> str:
    amount = f"{row.amount:,} ₽".replace(",", " ")
    lines = [
        "🏦 <b>Счёт на оплату — Пёс Дата</b>",
        "",
        f"Заявка: #{row.id}",
        f"Пакет: {row.package_name} ({row.contact_limit} контактов)",
        f"Сумма: {amount}",
        f"Плательщик: {row.company_name or '—'}",
        f"ИНН: {row.company_inn or '—'}",
        "",
        "Счёт во вложении. После оплаты пришлите, пожалуйста, платёжное поручение в этот чат.",
    ]
    return "\n".join(lines)


@app.post("/bank-payments/{request_id}/send-invoice")
async def bank_payment_send_invoice(
    request: Request,
    request_id: int,
    message: str = Form(""),
    file: UploadFile | None = File(None),
):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        row = await get_bank_payment(session, request_id)
        if not row or not row.user:
            return RedirectResponse(
                f"/bank-payments?msg={quote('Заявка не найдена')}",
                status_code=303,
            )
        body = (message or "").strip() or _default_bank_invoice_message(row)
        file_data: bytes | None = None
        file_name: str | None = None
        if file and file.filename:
            file_data = await file.read()
            if len(file_data) > 20 * 1024 * 1024:
                return RedirectResponse(
                    f"/bank-payments?msg={quote('Файл больше 20 МБ')}",
                    status_code=303,
                )
            file_name = file.filename
        if not file_data:
            return RedirectResponse(
                f"/bank-payments?msg={quote('Прикрепите файл счёта (PDF или др.)')}",
                status_code=303,
            )
        from services.telegram_outbox_service import enqueue_telegram_message

        await enqueue_telegram_message(
            session,
            row.user,
            body,
            source="admin.bank_invoice",
            file_name=file_name,
            file_data=file_data,
        )
        if row.status not in (BankPaymentStatus.PAID.value, BankPaymentStatus.CANCELED.value):
            row.status = BankPaymentStatus.INVOICED.value
        await session.commit()
    return RedirectResponse(
        f"/bank-payments?msg={quote('Счёт поставлен в очередь — клиент получит в Telegram от бота')}",
        status_code=303,
    )


@app.get("/tariffs-legacy", response_class=HTMLResponse)
async def tariffs_page(request: Request, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        tariffs = await list_all_tariffs_admin(session)
    return render(request, "tariffs.html", {"tariffs": tariffs, "msg": msg})


@app.get("/tariffs/new", response_class=HTMLResponse)
async def tariff_new_page(request: Request):
    if redirect := auth_guard(request):
        return redirect
    return render(request, "tariff_form.html", {"tariff": None})


@app.get("/tariffs/{tariff_id}/edit", response_class=HTMLResponse)
async def tariff_edit_page(request: Request, tariff_id: int):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        tariff = await session.get(Tariff, tariff_id)
    if not tariff:
        return RedirectResponse("/tariffs?msg=Тариф не найден", status_code=303)
    return render(request, "tariff_form.html", {"tariff": tariff})


@app.post("/tariffs/save")
async def tariff_save(
    request: Request,
    name: str = Form(...),
    emoji: str = Form(""),
    price: int = Form(...),
    contact_limit: int = Form(...),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_active: str = Form(""),
    tariff_id: Optional[int] = Form(default=None),
):
    if redirect := auth_guard(request):
        return redirect
    try:
        async with async_session() as session:
            await save_tariff(
                session,
                tariff_id=tariff_id,
                name=name,
                emoji=emoji,
                price=price,
                contact_limit=contact_limit,
                description=description,
                sort_order=sort_order,
                is_active=bool(is_active),
            )
        return RedirectResponse("/tariffs?msg=Тариф сохранён", status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/tariffs?msg={exc}", status_code=303)


@app.post("/tariffs/{tariff_id}/toggle")
async def tariff_toggle(request: Request, tariff_id: int):
    if redirect := auth_guard(request):
        return redirect
    try:
        async with async_session() as session:
            await toggle_tariff_active(session, tariff_id)
        return RedirectResponse("/tariffs?msg=Статус тарифа изменён", status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/tariffs?msg={exc}", status_code=303)


@app.get("/payments", response_class=HTMLResponse)
async def payments_page(request: Request, status: str = "", msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        stmt = (
            select(Payment)
            .options(selectinload(Payment.user), selectinload(Payment.tariff))
            .order_by(Payment.created_at.desc())
        )
        if status:
            stmt = stmt.where(Payment.status == status)
        payments = (await session.execute(stmt)).scalars().all()
    return render(
        request,
        "payments.html",
        {"payments": payments, "status": status, "labels": STATUS_LABELS, "msg": msg},
    )


@app.post("/payments/{payment_id}/sync")
async def payment_sync(request: Request, payment_id: int):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        payment = await session.get(Payment, payment_id)
        if not payment:
            return RedirectResponse("/payments?msg=Платёж не найден", status_code=303)
        result = await sync_pending_payment(session, payment)
    if result:
        user, order = result
        await notify_payment_success(user.telegram_id, order.contact_limit)
        return RedirectResponse(
            f"/payments?msg=Оплата активирована: @{user.username or user.telegram_id}",
            status_code=303,
        )
    return RedirectResponse(
        "/payments?msg=В ЮKassa оплата не подтверждена или уже обработана",
        status_code=303,
    )


@app.post("/payments/sync-pending")
async def payments_sync_pending(request: Request):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        activated = await sync_all_pending_payments(session)
    for user, order in activated:
        await notify_payment_success(user.telegram_id, order.contact_limit)
    count = len(activated)
    return RedirectResponse(
        f"/payments?status=pending&msg=Синхронизировано оплат: {count}",
        status_code=303,
    )


@app.get("/projects", response_class=HTMLResponse)
async def projects_page(
    request: Request,
    q: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
    msg: str = "",
):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        projects = await list_projects(
            session, q=q, status=status, date_from=date_from, date_to=date_to
        )
    return render(
        request,
        "projects.html",
        {
            "projects": projects,
            "q": q,
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
            "labels": STATUS_LABELS,
            "order_remaining": order_remaining,
            "format_purchase_date": format_purchase_date,
            "msg": msg,
        },
    )


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail_page(request: Request, project_id: int, mode: str = "", msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        project = await get_project_detail(session, project_id)
        if not project:
            return RedirectResponse("/projects?msg=Проект не найден", status_code=303)
        price = await get_order_price(session, project.order)
        activities = sorted(project.activity_logs, key=lambda a: a.created_at, reverse=True)
        deliveries = sorted(project.deliveries, key=lambda d: d.created_at, reverse=True)
        competitors = sorted(project.competitor_numbers, key=lambda c: c.created_at, reverse=True)
    return render(
        request,
        "project_detail.html",
        {
            "project": project,
            "price": price,
            "format_project_price": format_project_price,
            "activities": activities,
            "deliveries": deliveries,
            "competitors": competitors,
            "order_remaining": order_remaining,
            "labels": STATUS_LABELS,
            "delivery_type_label": delivery_type_label,
            "mode": mode,
            "msg": msg,
        },
    )


@app.get("/active-orders", response_class=HTMLResponse)
async def active_orders_page(request: Request, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        rows = await list_active_orders(session)
    return render(
        request,
        "active_orders.html",
        {
            "rows": rows,
            "labels": STATUS_LABELS,
            "order_remaining": order_remaining,
            "format_purchase_date": format_purchase_date,
            "msg": msg,
        },
    )


@app.get("/deliveries/history", response_class=HTMLResponse)
async def deliveries_history_page(request: Request):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        deliveries = await list_delivery_history(session)
    return render(
        request,
        "delivery_history.html",
        {
            "deliveries": deliveries,
            "delivery_type_label": delivery_type_label,
        },
    )


@app.get("/deliveries/{delivery_id}/download")
async def delivery_file_download(request: Request, delivery_id: int):
    if redirect := auth_guard(request):
        return redirect
    from fastapi.responses import Response

    async with async_session() as session:
        delivery = await session.get(Delivery, delivery_id)
    if not delivery or not delivery.file_data:
        return RedirectResponse("/deliveries/history", status_code=303)
    filename = delivery.file_name or f"delivery_{delivery_id}.txt"
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if filename.lower().endswith(".csv"):
        media_type = "text/csv"
    elif filename.lower().endswith(".txt"):
        media_type = "text/plain"
    return Response(
        content=delivery.file_data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, status: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        stmt = (
            select(Order)
            .options(selectinload(Order.user), selectinload(Order.tariff))
            .order_by(Order.created_at.desc())
        )
        if status:
            stmt = stmt.where(Order.status == status)
        orders = (await session.execute(stmt)).scalars().all()
    return render(
        request,
        "orders.html",
        {
            "orders": orders,
            "status": status,
            "labels": STATUS_LABELS,
            "order_remaining": order_remaining,
        },
    )


@app.post("/delivery/test-order")
async def delivery_test_order(request: Request, user_id: int = Form(...)):
    if redirect := auth_guard(request):
        return redirect
    try:
        async with async_session() as session:
            await create_test_order(session, user_id)
        return RedirectResponse(
            f"/delivery?user_id={user_id}&msg=Тестовый заказ создан (100 контактов)",
            status_code=303,
        )
    except ValueError as exc:
        return RedirectResponse(f"/delivery?user_id={user_id}&msg={exc}", status_code=303)


@app.get("/delivery", response_class=HTMLResponse)
async def delivery_page(
    request: Request,
    user_id: int = 0,
    mode: str = "",
    msg: str = "",
):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        users = (
            await session.execute(select(User).order_by(User.created_at.desc()))
        ).scalars().all()
        selected_user = None
        active_order = None
        competitor_count = 0
        if user_id:
            selected_user = await get_user_with_orders(session, user_id)
            if selected_user:
                active_order = next(
                    (
                        o
                        for o in selected_user.orders
                        if o.status
                        in (OrderStatus.ACTIVE.value, OrderStatus.IN_PROGRESS.value)
                    ),
                    None,
                )
                from sqlalchemy import func
                from database.models import CompetitorNumber, CompetitorStatus

                competitor_count = (
                    await session.scalar(
                        select(func.count(CompetitorNumber.id)).where(
                            CompetitorNumber.user_id == user_id,
                            CompetitorNumber.status == CompetitorStatus.ACTIVE.value,
                        )
                    )
                ) or 0
    return render(
        request,
        "delivery.html",
        {
            "users": users,
            "selected_user": selected_user,
            "active_order": active_order,
            "competitor_count": competitor_count,
            "user_id": user_id,
            "mode": mode,
            "msg": msg,
            "order_remaining": order_remaining,
            "labels": STATUS_LABELS,
            "format_purchase_date": format_purchase_date,
        },
    )


@app.post("/delivery/preview", response_class=HTMLResponse)
async def delivery_preview_view(
    request: Request,
    order_id: int = Form(...),
    delivery_type: str = Form(DeliveryType.MESSAGE.value),
    phones_text: str = Form(""),
    file: UploadFile | None = File(None),
):
    if redirect := auth_guard(request):
        return redirect

    phones: list[str] = []
    invalid = 0
    file_name: str | None = None
    file_data: bytes | None = None

    if delivery_type == DeliveryType.MESSAGE.value:
        if not phones_text.strip():
            return RedirectResponse(
                f"/delivery?msg={quote('Вставьте список номеров')}",
                status_code=303,
            )
        phones, invalid = parse_contacts_text(phones_text)
    else:
        if not file or not file.filename:
            return RedirectResponse(
                f"/delivery?msg={quote('Загрузите файл')}",
                status_code=303,
            )
        file_data = await file.read()
        file_name = file.filename
        if not file_data:
            return RedirectResponse(
                f"/delivery?msg={quote('Файл пуст')}",
                status_code=303,
            )
        phones, invalid = parse_contacts_file(file_data, file.filename)

    if not phones:
        async with async_session() as session:
            order = await session.get(Order, order_id)
            if order:
                await session.refresh(order, ["user"])
                user_id = order.user_id
            else:
                user_id = 0
        return RedirectResponse(
            f"/delivery?user_id={user_id}&msg={quote('Не найдено корректных номеров')}",
            status_code=303,
        )

    async with async_session() as session:
        preview = await preview_delivery(session, order_id, phones, invalid=invalid)
        order = await session.get(Order, order_id)
        await session.refresh(order, ["tariff", "user"])
        from services.project_service import get_project_by_order

        project = await get_project_by_order(session, order.id)

    phones_payload = phones_to_text(preview.phones)
    file_b64 = base64.b64encode(file_data).decode() if file_data else ""

    return render(
        request,
        "delivery_preview.html",
        {
            "preview": preview,
            "order": order,
            "project": project,
            "delivery_type": delivery_type,
            "phones_b64": base64.b64encode(phones_payload.encode()).decode(),
            "file_b64": file_b64,
            "file_name": file_name or "",
            "order_remaining": order_remaining,
            "invalid": invalid,
        },
    )


@app.post("/delivery/send")
async def delivery_send(
    request: Request,
    order_id: int = Form(...),
    delivery_type: str = Form(DeliveryType.MESSAGE.value),
    phones_b64: str = Form(...),
    file_b64: str = Form(""),
    file_name: str = Form(""),
    note: str = Form(""),
):
    if redirect := auth_guard(request):
        return redirect
    try:
        phones_text = base64.b64decode(phones_b64.encode()).decode()
        phones_e164 = []
        for line in phones_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            normalized = normalize_phone(line)
            if normalized:
                phones_e164.append(normalized)
    except Exception:
        return RedirectResponse("/delivery?msg=Ошибка данных формы", status_code=303)

    admin_id = get_admin_username(request)
    outbound_file_name = file_name or None
    outbound_file_data: bytes | None = None
    if delivery_type == DeliveryType.FILE.value:
        outbound_file_name = file_name or "contacts.txt"
        outbound_file_data = phones_text.encode("utf-8")
        if not outbound_file_name.lower().endswith((".txt", ".csv", ".xlsx")):
            outbound_file_name = "contacts.txt"

    try:
        async with async_session() as session:
            result = await commit_delivery(
                session,
                order_id,
                phones_e164,
                delivery_type=delivery_type,
                contacts_text=phones_text,
                file_name=outbound_file_name if delivery_type == DeliveryType.FILE.value else None,
                file_data=outbound_file_data if delivery_type == DeliveryType.FILE.value else None,
                admin_id=admin_id,
                note=note or None,
            )

        notify = await deliver_contacts_to_user(
            result.user_telegram_id,
            result.phones,
            result.received,
            result.limit,
            result.remaining,
            delivery_type=result.delivery_type,
            file_name=result.file_name,
            file_data=result.file_data,
        )

        if result.order_completed:
            await notify_package_completed(result.user_telegram_id)

        redirect_base = (
            f"/projects/{result.project_id}" if result.project_id else "/active-orders"
        )
        if not notify.ok:
            return RedirectResponse(
                f"{redirect_base}?msg="
                + quote("Сохранено в БД, но Telegram: " + (notify.error or "")),
                status_code=303,
            )
        msg = f"Отправлено {result.sent_count} конт."
        if notify.error:
            msg += f" (частично: {notify.error})"
        return RedirectResponse(f"{redirect_base}?msg={quote(msg)}", status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/delivery?msg={quote(str(exc))}", status_code=303)


@app.get("/admin/notifications", response_class=HTMLResponse)
async def admin_notifications_page(request: Request, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        cfg = await get_or_create_default_config(session)
    return render(
        request,
        "admin_notifications.html",
        {"cfg": cfg, "msg": msg, "env_admin_id": settings.admin_telegram_id or settings.admin_username or None},
    )


@app.post("/admin/notifications/save")
async def admin_notifications_save(
    request: Request,
    cfg_id: int = Form(...),
    telegram_id: int = Form(...),
    new_registration_enabled: str = Form(""),
    new_project_enabled: str = Form(""),
    payment_enabled: str = Form(""),
    competitor_added_enabled: str = Form(""),
    package_completed_enabled: str = Form(""),
    error_enabled: str = Form(""),
):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        await update_notification_config(
            session,
            cfg_id,
            telegram_id=telegram_id,
            new_registration_enabled=bool(new_registration_enabled),
            new_project_enabled=bool(new_project_enabled),
            payment_enabled=bool(payment_enabled),
            competitor_added_enabled=bool(competitor_added_enabled),
            package_completed_enabled=bool(package_completed_enabled),
            error_enabled=bool(error_enabled),
        )
    return RedirectResponse("/admin/notifications?msg=Настройки сохранены", status_code=303)


@app.post("/admin/notifications/daily-report")
async def admin_notifications_daily_report(request: Request):
    if redirect := auth_guard(request):
        return redirect
    await notify_admin_daily_report()
    return RedirectResponse("/admin/notifications?msg=Отчёт отправлен", status_code=303)


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        stats = await dashboard_stats(session)
        sales = await sales_by_day(session)
        popular = (
            await session.execute(
                select(Order.tariff_id, func.count(Order.id).label("cnt"))
                .group_by(Order.tariff_id)
                .order_by(func.count(Order.id).desc())
            )
        ).all()
    return render(request, "stats.html", {"stats": stats, "sales": sales, "popular": popular})
