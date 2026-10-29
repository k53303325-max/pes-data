# Только вы (Amvera + ONREZA) — ~5 минут

Всё остальное уже в GitHub (`amvera.yml`, код бота). Mac-poller **остановлен**.

## Amvera (cloud.amvera.ru)

1. **Переменные** → добавить:
   - `BOT_TOKEN` — из BotFather / как на ONREZA
   - `DATABASE_URL` — **скопировать из ONREZA** (Postgres Kaiki, одна строка)

2. **Конфигурация** — убедиться, что подтянулся `amvera.yml` (Python 3.12, `scripts/telegram_poller.py`). Если пусто — **Синхронизировать с Git** или вставить файл из репозитория.

3. **Регион:** Москва. **Тариф:** Пробный или Начальный.

4. Нажать **Собрать** (если после push сборка не стартовала сама).

5. **Логи** — должно быть: `Telegram long polling started`. Если `BOT_TOKEN` / `DATABASE_URL` — вернуться к п.1.

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
