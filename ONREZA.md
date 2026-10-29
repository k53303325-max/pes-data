# Пёс Дата — деплой на ONREZA

Проект в панели: [app.onreza.ru/k53303325-v03q/deployments](https://app.onreza.ru/k53303325-v03q/deployments)

ONREZA запускает **постоянный процесс** (uvicorn + FastAPI) — для **админки** это надёжнее, чем serverless на Vercel.

**Бот 24/7:** Telegram API с серверов ONREZA часто недоступен → бот крутится **отдельно** (`scripts/telegram_poller.py` на VPS или Mac). Подробно: [docs/BOT_24_7.md](docs/BOT_24_7.md).

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
| `ONREZA` | `1` |
| `TELEGRAM_BOT_DISABLED` | `1` — **рекомендуется**: бот не стартует внутри ONREZA (Telegram API с сервера часто недоступен). Бот — отдельно: `./venv/bin/python scripts/telegram_poller.py` на Mac/VPS с тем же `DATABASE_URL` и `BOT_TOKEN`. |
| `TELEGRAM_POLLING` | `1` — polling внутри ONREZA (только если API Telegram доступен с сервера) |
| `TELEGRAM_WEBHOOK` | не используйте на ONREZA, если polling/poller |

**Vercel:** авто-деплой отключён в `vercel.json`; бот на Vercel не запускается.
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
| Telegram | не используется при `TELEGRAM_BOT_DISABLED=1` + poller на VPS |
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

## Новая база ONREZA + старые пользователи (Neon)

1. Создай Postgres на ONREZA → скопируй `DATABASE_URL` в **TARGET**.
2. Neon → connection string в **SOURCE** (`POSTGRES_URL_NON_POOLING`).
3. На Mac:

```bash
export SOURCE_DATABASE_URL='postgresql://...neon...'
export TARGET_DATABASE_URL='postgresql://...onreza...'
./venv/bin/python scripts/migrate_old_database.py
```

4. В ONREZA оставь **TARGET** в `DATABASE_URL` → Redeploy.

Пользователи с одинаковым Telegram не дублируются (склеиваются по `telegram_id`).
