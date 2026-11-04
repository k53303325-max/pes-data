# Только вы (Amvera + ONREZA) — ~5 минут

Всё остальное уже в GitHub (`amvera.yml`, код бота). Mac-poller **остановлен**.

## Amvera (cloud.amvera.ru)

1. **Переменные** → добавить:
   - `BOT_TOKEN` — из BotFather / как на ONREZA
   - `DATABASE_URL` — строка Postgres (Kaiki). **Amvera не принимает `!` в поле** — в пароле замените `!` на **`%21`** (URL-encoding). Пример: `Kk1!xxx` → `Kk1%21xxx` внутри URL. Можно включить **«Это секрет»**.

2. **Конфигурация** — убедиться, что подтянулся `amvera.yml` (Python 3.12, `scripts/telegram_poller.py`). Если пусто — **Синхронизировать с Git** или вставить файл из репозитория.

3. **Регион:** Москва. **Тариф «Начальный» (~290 ₽/мес)** — «Пробный» (0.1 GB) даёт `Insufficient RAM`.

4. **Управление → Перезапустить** (обязательно после добавления переменных).

5. Если в логах «Не задано: BOT_TOKEN, DATABASE_URL» — переменные не попали в контейнер:
   - удалите и создайте снова как **секреты** (галочка «Это секрет»), этап **Запуск**;
   - **или** «Подгрузить .env»: файл из `deploy/amvera-dotenv.example` (две строки, `DATABASE_URL` с `%21` вместо `!`), затем снова **Перезапустить**.

6. **Логи** — сначала `DB ping ok`, затем `Telegram long polling started`. После push в Git дождитесь новой сборки.

7. **`TimeoutError` / asyncpg в логах** — контейнер **не достучался до Postgres** за ~45 с. Это не баг кнопок: пока нет БД, любой callback с сессией падает.
   - ONREZA `/health?deep=1` → `db_ready: true` значит база жива; проблема именно **между Amvera и Kaiki** или **неверный `DATABASE_URL` в Amvera**.
   - В логах Amvera после деплоя ищите строку `DATABASE_URL → host=ep-….kaiki.ru` — хост должен совпадать с ONREZA (PostgreSQL → строка подключения), не «внутренний» URL только для ONREZA.
   - С Mac проверка: `TARGET_DATABASE_URL='postgresql://…' python3 scripts/test_db_connect.py` → должно быть `OK` за несколько секунд. Если Mac OK, а Amvera `TimeoutError` — пересоздайте секрет `DATABASE_URL` на Amvera (**Подгрузить .env** из `deploy/amvera-dotenv.example`) или напишите в поддержку Amvera про исходящий доступ на `*.kaiki.ru:5432`.
   - Пароль на Amvera: `!` → `%21`. После правки — **Перезапустить**.
   - Запасной вариант 24/7: poller на **Timeweb VPS** (см. `docs/BOT_24_7.md`) с той же строкой — с домашнего Mac к Kaiki обычно подключается нормально.

## ONREZA (app.onreza.ru)

1. Environment → добавить или изменить:
   ```bash
   TELEGRAM_BOT_DISABLED=1
   ```
2. **Redeploy** production.

Проверка: https://pes-data-k53303325-v03q.onreza.app/health → `"telegram_mode":"off"`.

## Telegram

Отправить боту **`/start`**.

---

После Amvera бот **не должен** крутиться на Mac. Если снова запустите poller локально — будет конфликт с Amvera.
