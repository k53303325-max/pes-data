# Пёс Дата — Timeweb VPS + Postgres ONREZA + GitHub

**Схема:**

| Что | Где |
|-----|-----|
| **PostgreSQL (Kaiki)** | **ONREZA** — та же `DATABASE_URL`, что сейчас |
| **Админка + ЮKassa** | **Timeweb Cloud** (VPS) |
| **Telegram bot 24/7** | Тот же VPS → `pes-data-poller` |
| **Код** | **GitHub** → `git pull` на сервере |

ONREZA **приложение** (FastAPI) можно **выключить** — платите только за **базу**, если так устроен тариф.  
Amvera, Vercel — не используем.

Mac не нужен для работы бота.

---

## Этап 1 — Облачный сервер Timeweb

1. [timeweb.cloud](https://timeweb.cloud) → **Облачные серверы** → Ubuntu **22.04**.
2. **Cloud‑15** (1 vCPU, 1 GB, 15 GB), регион **РФ**, **публичный IPv4**.
3. SSH: `ssh root@ВАШ_IP`

---

## Этап 2 — Установка приложения

```bash
git clone https://github.com/k53303325-max/pes-data.git /opt/pes-data
bash /opt/pes-data/scripts/timeweb_install.sh
```

Секреты (скопируйте из панели **ONREZA → Postgres → строка подключения**):

```bash
nano /etc/pes-data.env
chmod 600 /etc/pes-data.env
```

Обязательно:

- `DATABASE_URL=postgresql://…@ep-….kaiki.ru:5432/…?sslmode=require` — **в пароле `!` → `%21`**
- `BOT_TOKEN`, `ADMIN_*`, `YOOKASSA_*`
- `APP_URL=https://admin.ваш-домен.ru` (после SSL; для первого теста можно `http://IP:8000` через nginx)
- `PES_DATA_VPS=1`
- `TELEGRAM_BOT_DISABLED=1` (бот только в poller)
- `PES_DATA_POLLER=1` (для poller, можно в том же файле)

Запуск:

```bash
systemctl enable --now pes-data-admin pes-data-poller
journalctl -u pes-data-poller -f
```

Ожидаем в логах poller: **`DB ping ok`**, **`Telegram long polling started`**.

Если **`TimeoutError`** до Kaiki — как на Amvera: напишите в поддержку Timeweb про исходящий **5432** к `*.kaiki.ru`. С Mac у вас подключение работало — с VPS обычно тоже должно.

---

## Этап 3 — Домен и HTTPS

1. A‑запись домена → IP VPS.
2. В `deploy/nginx/pes-data.conf.example` замените `server_name`, положите в nginx, затем:

```bash
certbot --nginx -d admin.ваш-домен.ru
```

3. `APP_URL=https://admin.ваш-домен.ru` в `/etc/pes-data.env`
4. `systemctl restart pes-data-admin`

**ЮKassa:** webhook → `https://admin.ваш-домен.ru/yookassa/webhook`

---

## Этап 4 — Выключить лишнее

| | |
|---|---|
| **ONREZA deploy** (сайт) | Redeploy не нужен / остановить приложение — **база Kaiki остаётся** |
| **Amvera** | остановить |
| **Mac poller** | `pkill -f scripts/telegram_poller.py` |

---

## Обновление с GitHub

```bash
cd /opt/pes-data && git pull
./venv/bin/pip install -r requirements.txt -q
sudo systemctl restart pes-data-admin pes-data-poller
```

---

## Проверка

- `https://admin.…/health` → `"platform":"timeweb"`, `"db_ready":true`
- Telegram `/start` без Mac
- Админка: логин, пользователи из Kaiki

---

## Переменные

Полный пример: `deploy/timeweb.env.example`

**Миграция БД не нужна** — данные остаются в ONREZA/Kaiki.
