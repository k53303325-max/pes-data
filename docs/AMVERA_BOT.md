# Бот на Amvera (24/7 без Mac)

Админка — **ONREZA**. Бот — **отдельное приложение Amvera** из того же GitHub-репозитория.

## 1. Подготовка ONREZA

В переменных окружения ONREZA:

```bash
TELEGRAM_BOT_DISABLED=1
```

Redeploy. В `/health` должно быть `"telegram_mode":"off"`.

## 2. Создать приложение на Amvera

1. [cloud.amvera.ru](https://cloud.amvera.ru) → регистрация / вход.
2. **Создать приложение** → **Git** → репозиторий `k53303325-max/pes-data`, ветка `main`.
3. **Регион:** **Москва** (у Amvera есть прокси до Telegram API из РФ).
4. Amvera подхватит **`amvera.yml`** в корне — запуск `scripts/telegram_poller.py`.

Если конфиг не подтянулся: раздел **Конфигурация** → вставить содержимое `amvera.yml` из репозитория.

## 3. Переменные окружения (Amvera → Переменные)

| Переменная | Значение |
|------------|----------|
| `BOT_TOKEN` | как на ONREZA |
| `DATABASE_URL` | **та же** строка Postgres (Kaiki), что в ONREZA |

`.env` в репозиторий не кладём — только в панели Amvera.

## 4. Сборка и запуск

- **Собрать** / дождаться деплоя после push в `main`.
- Логи: в приложении Amvera → **Логи** — строки `Telegram long polling started`.

## 5. Остановить Mac-poller

На Mac (иначе два процесса с одним токеном):

```bash
pkill -f scripts/telegram_poller.py
```

## 6. Проверка

- Telegram: `/start` — ответ за несколько секунд.
- [getWebhookInfo](https://core.telegram.org/bots/api#getwebhookinfo): `url` пустой (режим polling).

## Если не отвечает

1. Логи Amvera — ошибки `asyncpg`, `BOT_TOKEN`, traceback при импорте handlers.
2. Регион **Москва** или **Варшава/Майами** (см. [bothosting](https://amvera.ru/bothosting)).
3. `DATABASE_URL` без опечаток, SSL-хост `kaiki.ru` доступен с Amvera.

## Два хостинга — один репозиторий

| Файл | Кто читает |
|------|------------|
| `onreza.toml` | ONREZA (админка) |
| `amvera.yml` | Amvera (только бот) |

Push в `main` обновляет **оба** проекта, если оба подключены к Git — это нормально: ONREZA не запускает бота при `TELEGRAM_BOT_DISABLED=1`.
