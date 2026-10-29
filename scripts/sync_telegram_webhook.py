#!/usr/bin/env python3
"""Поставить Telegram webhook на APP_URL (ONREZA / production)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

CANDIDATE_URLS = [
    os.getenv("APP_URL", "").strip().rstrip("/"),
    os.getenv("ONREZA_APP_URL", "").strip().rstrip("/"),
    "https://v03q-k53303325-workspace.onreza.app",
    "https://k53303325-v03q-workspace.onreza.app",
    "https://pes-data-k53303325-workspace.onreza.app",
]


def _http_get(url: str, timeout: float = 10.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "pes-data-webhook-sync"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")[:500]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")[:500]
    except Exception as exc:
        return 0, str(exc)


def discover_app_url() -> str | None:
    seen: set[str] = set()
    for raw in CANDIDATE_URLS:
        if not raw or raw in seen:
            continue
        seen.add(raw)
        status, body = _http_get(f"{raw}/health")
        if status == 200 and '"ok"' in body and "true" in body.lower():
            return raw
    return None


def telegram_api(token: str, method: str, payload: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    token = (os.getenv("BOT_TOKEN") or "").strip()
    if not token:
        print("BOT_TOKEN не задан", file=sys.stderr)
        return 1

    app_url = (sys.argv[1] if len(sys.argv) > 1 else "").strip().rstrip("/")
    if not app_url:
        app_url = discover_app_url()
    if not app_url:
        print(
            "Не найден живой APP_URL (/health). Укажите URL:\n"
            "  python scripts/sync_telegram_webhook.py https://ваш-проект.onreza.app",
            file=sys.stderr,
        )
        info = telegram_api(token, "getWebhookInfo")
        print("Текущий webhook:", info.get("result", {}).get("url"))
        print("Ошибка:", info.get("result", {}).get("last_error_message"))
        return 1

    webhook_url = f"{app_url}/webhook/telegram"
    status, body = _http_get(f"{app_url}/health")
    print(f"health {status}: {body[:120]}")

    result = telegram_api(
        token,
        "setWebhook",
        {"url": webhook_url, "drop_pending_updates": False},
    )
    if not result.get("ok"):
        print("setWebhook failed:", result, file=sys.stderr)
        return 1

    info = telegram_api(token, "getWebhookInfo")
    print("Webhook установлен:", info.get("result", {}).get("url"))
    print("Pending updates:", info.get("result", {}).get("pending_update_count"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
