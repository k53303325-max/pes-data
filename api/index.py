from __future__ import annotations

import json
import traceback

try:
    from mangum import Mangum

    from admin_web.app import app

    _mangum = Mangum(app, lifespan="off")

    def handler(event, context):
        return _mangum(event, context)

except Exception:
    _BOOT_ERROR = traceback.format_exc()

    def handler(event, context):  # noqa: F811
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
            "body": "Import failed:\n" + _BOOT_ERROR,
        }
