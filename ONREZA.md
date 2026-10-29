# Пёс Дата — деплой на ONREZA

Проект в панели: [app.onreza.ru/k53303325-v03q/deployments](https://app.onreza.ru/k53303325-v03q/deployments)

ONREZA запускает **постоянный процесс** (uvicorn + FastAPI) — для Telegram-бота и админки это надёжнее, чем serverless на Vercel.

## 1. Репозиторий

Подключите GitHub-репозиторий `k53303325-max/pes-data` в настройках проекта ONREZA (ветка `main`).

В корне уже есть `onreza.toml`:

```toml
[deploy]
application = "admin_web.app:app"
server = "uvicorn"
```

## 2. Переменные окружения

В **Settings → Environment Variables** (production) задайте:

| Переменная | Назначение |
|------------|------------|
| `ONREZA` | `1` — включает webhook-режим бота |
| `APP_URL` | Публичный URL приложения **без** слэша в конце, например `https://ваш-проект.onreza.app` |
| `BOT_TOKEN` | Токен @Pesdata_bot |
| `DATABASE_URL` | PostgreSQL (`postgresql://…`) |
| `ADMIN_PASSWORD` | Пароль админки |
| `ADMIN_SECRET_KEY` | Секрет сессий (длинная случайная строка) |
| `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` | ЮKassa |
| `PROMO_TEST_CODE` | Промокод для тестов (например `PESDATA100`) |
| `ADMIN_ID` | Telegram ID админа для уведомлений |

Остальное — по `.env.example`.

**Важно:** после первого деплоя скопируйте выданный production URL в `APP_URL` и сделайте **Redeploy** — иначе Telegram webhook укажет не туда.

## 3. Webhook’и

| Сервис | URL |
|--------|-----|
| Telegram | `{APP_URL}/webhook/telegram` (ставится автоматически при старте) |
| ЮKassa | `{APP_URL}/yookassa/webhook` |

## 4. Деплой из CLI (опционально)

```bash
curl -fsSL https://raw.githubusercontent.com/ONREZA/nrz-cli/main/install.sh | bash
nrz login
cd /path/to/pes-data
nrz deploy --environment production
```

Документация: [docs.onreza.ru](https://docs.onreza.ru/getting-started.html)

## 5. Проверка

1. `GET {APP_URL}/health` → `{"ok": true, "platform": "onreza"}`
2. `{APP_URL}/login` — форма входа
3. В Telegram: `/start` — меню бота

## Локально

```bash
source venv/bin/activate
pip install -r requirements.txt
python run_admin.py
```

Polling-бот (без webhook): `python main.py` — только для разработки.
