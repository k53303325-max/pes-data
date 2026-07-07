#!/bin/bash
# Остановить все экземпляры бота
cd "$(dirname "$0")"

if [ -f ".bot.pid" ]; then
  kill "$(cat .bot.pid)" 2>/dev/null
  rm -f .bot.pid
fi

pkill -f "python main.py" 2>/dev/null
echo "✅ Бот остановлен"
