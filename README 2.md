# Пёс Дата

Платформа лидогенерации — определяет посетителей сайтов конкурентов и передаёт клиентам их номера телефонов.

## Стек

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Backend:** Next.js API Routes
- **БД:** PostgreSQL + Prisma
- **Авторизация:** NextAuth.js

## Быстрый старт

```bash
npm install
cp .env.example .env
# Настройте DATABASE_URL и NEXTAUTH_SECRET
npx prisma db push
npm run db:seed
npm run dev
```

Откройте [http://localhost:3000](http://localhost:3000)

### Демо-аккаунты

| Роль | Email | Пароль |
|------|-------|--------|
| Клиент | demo@pesdata.ru | demo123 |
| Админ | admin@pesdata.ru | admin123 |

## Структура

- `/` — лендинг
- `/login`, `/register` — авторизация
- `/dashboard` — личный кабинет
- `/dashboard/leads` — лента номеров
- `/admin` — панель администратора

## API

- `POST /api/leads/incoming` — webhook для входящих лидов
- `GET /api/leads` — список лидов с фильтрами
- `POST /api/leads/fetch` — получить новые лиды
- `GET/POST /api/projects` — управление проектами
- `GET /api/stats` — статистика

## Деплой на Vercel

1. Подключите PostgreSQL (Neon, Supabase, Vercel Postgres)
2. Установите переменные окружения: `DATABASE_URL`, `NEXTAUTH_URL`, `NEXTAUTH_SECRET`
3. Deploy через Vercel CLI или GitHub integration

## Бренд

- Тёмно-синий: `#1E1E3A`
- Фиолетовый: `#5B5FC7`
- Светлый фон: `#F4F4FC`
