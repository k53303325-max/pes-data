# Пёс Дата — всё на Vercel

## Быстрая настройка (2 минуты)

### 1. Подключить базу в Vercel (без neon.tech)

1. [vercel.com/dashboard](https://vercel.com/dashboard) → проект **pes-data**
2. Вкладка **Storage** → **Create Database** → **Postgres**
3. **Create** → **Connect to pes-data**
4. **Deployments** → последний деплой → **Redeploy**

Vercel сам добавит `POSTGRES_URL` — ничего копировать не нужно.

### 2. Готово

| Что | URL |
|-----|-----|
| **Админка** | https://pes-data.vercel.app/login |
| **Бот Telegram** | работает автоматически (webhook) |

**Логин:** `admin`  
**Пароль:** см. Vercel → Settings → Environment Variables → `ADMIN_PASSWORD`

---

## Локальная разработка

```bash
source venv/bin/activate
python run_admin.py   # админка http://127.0.0.1:8000
python main.py        # бот (polling, отдельно)
```

Локально используется SQLite (`pes_data.db`).

---

## Переменные Vercel

| Переменная | Откуда |
|------------|--------|
| `POSTGRES_URL` | Автоматически при Storage → Postgres |
| `BOT_TOKEN` | Telegram @BotFather |
| `ADMIN_LOGIN` | Вручную |
| `ADMIN_PASSWORD` | Вручную |
| `ADMIN_SECRET_KEY` | Вручную (случайная строка) |
| `YOOKASSA_SHOP_ID` | [yookassa.ru](https://yookassa.ru) → Настройки → Ключи API |
| `YOOKASSA_SECRET_KEY` | Секретный ключ из личного кабинета ЮKassa |
| `YOOKASSA_RETURN_URL` | `https://t.me/Pesdata_bot` (после оплаты) |

### 3. Webhook ЮKassa

В личном кабинете ЮKassa → **Интеграция** → **HTTP-уведомления**:

```
https://pes-data.vercel.app/yookassa/webhook
```

Событие: **payment.succeeded**
