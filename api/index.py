from __future__ import annotations

import json


def _request_path(event) -> str:
    if isinstance(event, dict):
        return event.get("rawPath") or event.get("path") or ""
    return ""


def handler(event, context):
    """Vercel отключён — бот и админка только на ONREZA."""
    path = _request_path(event)
    if path.rstrip("/") == "/health":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": False, "deprecated": "use ONREZA"}),
        }
    return {
        "statusCode": 410,
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
        "body": "Пёс Дата переехал на ONREZA: https://pes-data-k53303325-v03q.onreza.app",
    }
