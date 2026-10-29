# Только вы (Amvera + ONREZA) — ~5 минут

Всё остальное уже в GitHub (`amvera.yml`, код бота). Mac-poller **остановлен**.

## Amvera (cloud.amvera.ru)

1. **Переменные** → добавить:
   - `BOT_TOKEN` — из BotFather / как на ONREZA
   - `DATABASE_URL` — строка Postgres (Kaiki). **Amvera не принимает `!` в поле** — в пароле замените `!` на **`%21`** (URL-encoding). Пример: `Kk1!xxx` → `Kk1%21xxx` внутри URL. Можно включить **«Это секрет»**.

2. **Конфигурация** — убедиться, что подтянулся `amvera.yml` (Python 3.12, `scripts/telegram_poller.py`). Если пусто — **Синхронизировать с Git** или вставить файл из репозитория.

3. **Регион:** Москва. **Тариф:** Пробный или Начальный.

4. **Управление → Перезапустить** (обязательно после добавления переменных).

5. Если в логах «Не задано: BOT_TOKEN, DATABASE_URL» — переменные не попали в контейнер:
   - удалите и создайте снова как **секреты** (галочка «Это секрет»), этап **Запуск**;
   - **или** «Подгрузить .env»: файл из `deploy/amvera-dotenv.example` (две строки, `DATABASE_URL` с `%21` вместо `!`), затем снова **Перезапустить**.

6. **Логи** — `Telegram long polling started`. После push в Git дождитесь новой сборки.

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
