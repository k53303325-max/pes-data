from __future__ import annotations

import json
import traceback


def _request_path(event) -> str:
    if isinstance(event, dict):
        return event.get("rawPath") or event.get("path") or ""
    return ""


def handler(event, context):
    path = _request_path(event)
    if path.rstrip("/") == "/health":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": True, "probe": "api-index"}),
        }

    try:
        from mangum import Mangum

        from admin_web.app import app

        if not hasattr(handler, "_mangum"):
            handler._mangum = Mangum(app, lifespan="off")  # type: ignore[attr-defined]
        return handler._mangum(event, context)  # type: ignore[attr-defined]
    except Exception:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
            "body": "Boot failed:\n" + traceback.format_exc(),
        }
