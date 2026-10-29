from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

from config.db_url import get_app_url, resolve_database_url, resolve_yookassa_return_url

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _clean_env(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip('"').strip("'")


def _int_env(key: str, default: int) -> int:
    raw = _clean_env(os.getenv(key))
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_admin_settings() -> tuple[int, str]:
    admin_id_raw = _clean_env(os.getenv("ADMIN_ID", "0")) or "0"
    admin_username = _clean_env(os.getenv("ADMIN_USERNAME", "")).lstrip("@")
    try:
        return int(admin_id_raw), admin_username
    except ValueError:
        if not admin_username:
            admin_username = admin_id_raw.lstrip("@")
        return 0, admin_username


@dataclass(frozen=True)
class Settings:
    bot_token: str
    bot_username: str
    admin_telegram_id: int
    admin_username: str
    database_url: str
    app_url: str
    yookassa_shop_id: str
    yookassa_secret_key: str
    yookassa_return_url: str
    webhook_host: str
    webhook_port: int
    yookassa_webhook_path: str
    add_rate_limit: int
    add_rate_window: int
    log_level: str
    log_file: Path
    admin_login: str
    admin_password: str
    admin_secret_key: str
    admin_host: str
    admin_port: int
    is_vercel: bool
    is_onreza: bool
    use_webhook: bool
    telegram_polling: bool
    telegram_bot_enabled: bool
    promo_test_code: str
    allow_mock_payment: bool
    referral_commission_percent: int
    referral_payout_hold_days: int


def get_settings() -> Settings:
    admin_telegram_id, admin_username = _parse_admin_settings()
    is_vercel = os.getenv("VERCEL") == "1"
    is_onreza = (
        os.getenv("ONREZA") == "1"
        or bool(_clean_env(os.getenv("NRZ_PROJECT_ID")))
        or os.getenv("USER") == "onreza"
    )
    database_url = resolve_database_url()
    hosted_on_onreza_db = "kaiki.ru" in database_url
    onreza_host = is_onreza or hosted_on_onreza_db
    bot_token = _clean_env(os.getenv("BOT_TOKEN"))
    if is_vercel:
        telegram_polling = False
        use_webhook = False
    else:
        telegram_polling = os.getenv("TELEGRAM_POLLING") == "1"
        use_webhook = (
            onreza_host or os.getenv("WEBHOOK_MODE") == "1"
        ) and not telegram_polling
    telegram_bot_enabled = (
        bool(bot_token)
        and not is_vercel
        and os.getenv("TELEGRAM_BOT_DISABLED") != "1"
    )
    return Settings(
        bot_token=bot_token,
        bot_username=_clean_env(os.getenv("BOT_USERNAME", "Pesdata_bot")).lstrip("@"),
        admin_telegram_id=admin_telegram_id,
        admin_username=admin_username,
        database_url=database_url,
        app_url=get_app_url(),
        yookassa_shop_id=_clean_env(os.getenv("YOOKASSA_SHOP_ID")),
        yookassa_secret_key=_clean_env(os.getenv("YOOKASSA_SECRET_KEY")),
        yookassa_return_url=resolve_yookassa_return_url(),
        webhook_host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
        webhook_port=_int_env("WEBHOOK_PORT", 8080),
        yookassa_webhook_path=os.getenv("YOOKASSA_WEBHOOK_PATH", "/yookassa/webhook"),
        add_rate_limit=_int_env("ADD_RATE_LIMIT", 5),
        add_rate_window=_int_env("ADD_RATE_WINDOW", 60),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=BASE_DIR / os.getenv("LOG_FILE", "logs/bot.log"),
        admin_login=os.getenv("ADMIN_LOGIN", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", "admin123"),
        admin_secret_key=os.getenv("ADMIN_SECRET_KEY", "change-me-secret-key"),
        admin_host=os.getenv("ADMIN_HOST", "127.0.0.1"),
        admin_port=_int_env("ADMIN_PORT", 8000),
        is_vercel=is_vercel,
        is_onreza=is_onreza,
        use_webhook=use_webhook,
        telegram_polling=telegram_polling,
        telegram_bot_enabled=telegram_bot_enabled,
        promo_test_code=os.getenv(
            "PROMO_TEST_CODE",
            "PESDATA100",
        ),
        allow_mock_payment=(
            os.getenv("ALLOW_MOCK_PAYMENT") == "1" and not is_vercel and not is_onreza
        ),
        referral_commission_percent=_int_env("REFERRAL_COMMISSION_PERCENT", 10),
        referral_payout_hold_days=_int_env("REFERRAL_PAYOUT_HOLD_DAYS", 14),
    )


settings = get_settings()
