"""Запуск админ-панели: uvicorn admin_web.app:app --reload --port 8000"""

import uvicorn

from config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "admin_web.app:app",
        host=settings.admin_host,
        port=settings.admin_port,
        reload=False,
    )
