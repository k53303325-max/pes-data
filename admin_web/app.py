from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.middleware.sessions import SessionMiddleware

from admin_web.auth import check_credentials, is_authenticated, login, logout
from bot.factory import ensure_telegram_webhook, get_bot, get_dispatcher
from config.settings import settings
from database.database import async_session, init_db
from database.models import (
    ContactDelivery,
    Order,
    OrderStatus,
    Payment,
    User,
    UserStatus,
)
from services.admin_stats_service import dashboard_stats, list_users, sales_by_day
from services.delivery_service import commit_delivery, parse_contacts_file, preview_delivery
from services.telegram_notify import notify_new_contacts
from services.user_service import get_user_with_orders, order_remaining

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))


def render(request: Request, name: str, context: dict | None = None):
    return templates.TemplateResponse(request, name, context or {})

app = FastAPI(title="Пёс Дата Admin")

_db_initialized = False


async def _ensure_db() -> None:
    global _db_initialized
    if not _db_initialized:
        await init_db()
        await ensure_telegram_webhook()
        _db_initialized = True


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
    https_only=settings.is_vercel,
)

if not settings.is_vercel:
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
}


@app.middleware("http")
async def init_db_middleware(request: Request, call_next):
    if settings.is_vercel and not settings.database_url:
        if request.url.path == "/webhook/telegram":
            return HTMLResponse('{"ok":false,"error":"no db"}', status_code=503)
        return HTMLResponse(DB_SETUP_HTML, status_code=503)
    try:
        await _ensure_db()
    except Exception as exc:
        return HTMLResponse(
            f"<h1>Ошибка подключения к БД</h1><pre>{exc}</pre>"
            "<p>Vercel → Storage → Postgres → Connect → Redeploy</p>",
            status_code=503,
        )
    return await call_next(request)


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Telegram Bot webhook — работает на Vercel без polling."""
    from aiogram.types import Update

    if not settings.bot_token:
        return {"ok": False, "error": "BOT_TOKEN not set"}

    data = await request.json()
    bot = get_bot()
    dp = get_dispatcher()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}


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
        login(request)
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
    return render(request, "dashboard.html", {"stats": stats, "labels": STATUS_LABELS})


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, q: str = "", status: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        users = await list_users(session, q, status)
    return render(
        request,
        "users.html",
        {"users": users, "q": q, "status": status, "labels": STATUS_LABELS},
    )


@app.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        user = await get_user_with_orders(session, user_id)
        if not user:
            return RedirectResponse("/users", status_code=303)
        deliveries = (
            await session.execute(
                select(ContactDelivery)
                .where(ContactDelivery.user_id == user_id)
                .order_by(ContactDelivery.created_at.desc())
            )
        ).scalars().all()
    return render(
        request,
        "user_detail.html",
        {
            "user": user,
            "deliveries": deliveries,
            "labels": STATUS_LABELS,
            "order_remaining": order_remaining,
        },
    )


@app.get("/payments", response_class=HTMLResponse)
async def payments_page(request: Request, status: str = ""):
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
        {"payments": payments, "status": status, "labels": STATUS_LABELS},
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


@app.get("/delivery", response_class=HTMLResponse)
async def delivery_page(request: Request, user_id: int = 0, msg: str = ""):
    if redirect := auth_guard(request):
        return redirect
    async with async_session() as session:
        users = (
            await session.execute(select(User).order_by(User.created_at.desc()))
        ).scalars().all()
        selected_user = None
        active_order = None
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
    return render(
        request,
        "delivery.html",
        {
            "users": users,
            "selected_user": selected_user,
            "active_order": active_order,
            "user_id": user_id,
            "msg": msg,
            "order_remaining": order_remaining,
        },
    )


@app.post("/delivery/preview", response_class=HTMLResponse)
async def delivery_preview_view(
    request: Request,
    order_id: int = Form(...),
    file: UploadFile = File(...),
):
    if redirect := auth_guard(request):
        return redirect
    content = await file.read()
    phones = parse_contacts_file(content, file.filename or "file.txt")
    async with async_session() as session:
        preview = await preview_delivery(session, order_id, phones)
        order = await session.get(Order, order_id)
        await session.refresh(order, ["tariff", "user"])
    return render(
        request,
        "delivery_preview.html",
        {
            "preview": preview,
            "order": order,
            "phones_csv": ",".join(preview.phones),
            "order_remaining": order_remaining,
        },
    )


@app.post("/delivery/send")
async def delivery_send(
    request: Request,
    order_id: int = Form(...),
    phones_csv: str = Form(...),
    note: str = Form(""),
):
    if redirect := auth_guard(request):
        return redirect
    phones = [p.strip() for p in phones_csv.split(",") if p.strip()]
    try:
        async with async_session() as session:
            result = await commit_delivery(session, order_id, phones, note or None)
        await notify_new_contacts(
            result.user_telegram_id,
            result.sent_count,
            result.received,
            result.limit,
            result.remaining,
        )
        return RedirectResponse(
            f"/delivery?user_id={result.user_db_id}&msg=Отправлено {result.sent_count} контактов",
            status_code=303,
        )
    except ValueError as exc:
        return RedirectResponse(f"/delivery?msg={exc}", status_code=303)


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
