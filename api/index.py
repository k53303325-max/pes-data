from __future__ import annotations

import traceback

try:
    from mangum import Mangum

    from admin_web.app import app

    _handler = Mangum(app, lifespan="off")

    def handler(event, context):
        return _handler(event, context)

except Exception:
    _BOOT_TRACEBACK = traceback.format_exc()

    def handler(event, context):  # noqa: F811
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
            "body": "Boot failed:\n" + _BOOT_TRACEBACK,
        }
