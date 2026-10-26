from __future__ import annotations

from typing import Optional

from fastapi import Request
from starlette.middleware.sessions import SessionMiddleware

from config.settings import settings

SESSION_KEY = "admin_authenticated"
ADMIN_USER_KEY = "admin_username"


def is_authenticated(request: Request) -> bool:
    return request.session.get(SESSION_KEY) is True


def login(request: Request, username: str = "") -> None:
    request.session[SESSION_KEY] = True
    request.session[ADMIN_USER_KEY] = username or settings.admin_login


def get_admin_username(request: Request) -> str:
    return request.session.get(ADMIN_USER_KEY) or settings.admin_login


def logout(request: Request) -> None:
    request.session.clear()


def check_credentials(login: str, password: str) -> bool:
    return login == settings.admin_login and password == settings.admin_password


def get_session_middleware() -> SessionMiddleware:
    return SessionMiddleware(
        secret_key=settings.admin_secret_key,
        session_cookie="pes_admin_session",
        max_age=86400 * 7,
        same_site="lax",
        https_only=False,
    )
