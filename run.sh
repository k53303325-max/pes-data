#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "Создаю виртуальное окружение..."
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
else
  source venv/bin/activate
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "❌ Создан .env — заполните BOT_TOKEN и перезапустите"
  read -p "Нажмите Enter..."
  exit 1
fi

mkdir -p logs

# Защита от двойного запуска
if [ -f ".bot.pid" ] && kill -0 "$(cat .bot.pid)" 2>/dev/null; then
  echo "❌ Бот уже запущен (PID $(cat .bot.pid)). Закройте другой терминал."
  read -p "Нажмите Enter..."
  exit 1
fi

echo "======================================"
echo "  🐕 Пёс Дата — бот запускается..."
echo "  НЕ ЗАКРЫВАЙТЕ это окно!"
echo "  Telegram: @Pesdata_bot"
echo "======================================"
echo ""

python main.py &
BOT_PID=$!
echo $BOT_PID > .bot.pid
wait $BOT_PID
rm -f .bot.pid

echo ""
echo "Бот остановлен. Нажмите Enter для выхода..."
read
