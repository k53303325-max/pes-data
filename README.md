# Пёс Дата

Telegram-бот + админ-панель для SaaS-платформы лидогенерации.

## Продакшен

См. **[docs/TIMEWEB.md](docs/TIMEWEB.md)** — **VPS Timeweb** (админка + bot 24/7) + **PostgreSQL ONREZA (Kaiki)** + **GitHub**.

## Локальная разработка

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # SQLite локально
python run_admin.py    # http://127.0.0.1:8000
python scripts/telegram_poller.py   # бот отдельно
```

## Этап 1 — /start

- Новый пользователь → приветствие + кнопки (Выбрать пакет, Как работает, FAQ)
- Вернувшийся с активным пакетом → статус пакета
- Завершённый пакет → предложение купить новый

Статусы: `new`, `active`, `finished`, `blocked`

## Админ-панель

| Раздел | Описание |
|--------|----------|
| Dashboard | KPI: пользователи, пакеты, оплаты, контакты |
| Пользователи | Поиск, фильтры, карточка клиента |
| Оплаты | Все платежи |
| Заказы | Контроль пакетов |
| Отправка контактов | Загрузка TXT/CSV/XLSX → отправка в Telegram |
| Статистика | Продажи, популярные тарифы |

## Устаревшие деплои

- [VERCEL.md](VERCEL.md) — не используется
- [ONREZA.md](ONREZA.md) — заменён на Timeweb
- [docs/AMVERA_BOT.md](docs/AMVERA_BOT.md) — не используется
