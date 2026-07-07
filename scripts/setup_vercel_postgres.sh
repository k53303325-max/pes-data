#!/usr/bin/env bash
# Подключение Postgres к pes-data на Vercel и redeploy.
set -euo pipefail

cd "$(dirname "$0")/.."

VERCEL="npm exec --yes --package=vercel@54.21.0 -- vercel"

echo "🐶 Пёс Дата — настройка Postgres на Vercel"
echo ""
echo "Если ещё не приняли условия Neon, откройте в браузере (нужен вход в Vercel):"
echo "  https://vercel.com/kates-projects-ad4765fe/~/integrations/accept-terms/neon?source=cli"
echo ""
echo "Или через Dashboard: pes-data → Storage → Create Database → Postgres"
echo ""

# 1. Принять условия (только в интерактивном терминале пользователя)
if [[ -t 0 ]]; then
  echo "→ Принимаем условия Neon (если нужно)..."
  $VERCEL integration accept-terms neon || true
fi

# 2. Создать базу и подключить к проекту
echo "→ Создаём Postgres..."
if ! $VERCEL integration add neon \
  --name pes-data-db \
  --plan free_v3 \
  -e production \
  -m region=iad1 \
  -m auth=false \
  --format=json 2>&1 | tee /tmp/pes-neon-install.log; then
  if grep -q "integration_terms_acceptance_required" /tmp/pes-neon-install.log 2>/dev/null; then
    echo ""
    echo "❌ Нужно принять условия в браузере (ссылка выше), затем запустите скрипт снова."
    exit 1
  fi
fi

# 3. Ждём POSTGRES_URL (пров provisioning 1–3 мин)
echo "→ Ждём POSTGRES_URL..."
for i in $(seq 1 36); do
  if $VERCEL env ls production 2>/dev/null | grep -q POSTGRES_URL; then
    echo "   POSTGRES_URL найден."
    break
  fi
  if [[ $i -eq 36 ]]; then
    echo "❌ POSTGRES_URL не появился за 3 минуты. Проверьте Vercel → Storage."
    exit 1
  fi
  sleep 5
done

# 4. Redeploy
echo "→ Деплой на production..."
$VERCEL --prod --yes

echo ""
echo "✅ Готово!"
echo "   Админка: https://pes-data.vercel.app/login"
echo "   Бот:     webhook настроится автоматически"
