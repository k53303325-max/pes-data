from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

from config.db_url import get_app_url, resolve_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_telegram_id: int
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


def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_telegram_id=int(os.getenv("ADMIN_ID", "0")),
        database_url=resolve_database_url(),
        app_url=get_app_url(),
        yookassa_shop_id=os.getenv("YOOKASSA_SHOP_ID", ""),
        yookassa_secret_key=os.getenv("YOOKASSA_SECRET_KEY", ""),
        yookassa_return_url=os.getenv("YOOKASSA_RETURN_URL", "https://t.me/"),
        webhook_host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
        webhook_port=int(os.getenv("WEBHOOK_PORT", "8080")),
        yookassa_webhook_path=os.getenv("YOOKASSA_WEBHOOK_PATH", "/yookassa/webhook"),
        add_rate_limit=int(os.getenv("ADD_RATE_LIMIT", "5")),
        add_rate_window=int(os.getenv("ADD_RATE_WINDOW", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=BASE_DIR / os.getenv("LOG_FILE", "logs/bot.log"),
        admin_login=os.getenv("ADMIN_LOGIN", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", "admin123"),
        admin_secret_key=os.getenv("ADMIN_SECRET_KEY", "change-me-secret-key"),
        admin_host=os.getenv("ADMIN_HOST", "127.0.0.1"),
        admin_port=int(os.getenv("ADMIN_PORT", "8000")),
        is_vercel=os.getenv("VERCEL") == "1",
    )


settings = get_settings()
