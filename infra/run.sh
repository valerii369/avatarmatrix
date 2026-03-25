#!/bin/bash
# AVATAR — запуск backend + bot
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🚀 Запуск AVATAR..."

# Переходим в backend
cd "${PROJECT_ROOT}/backend"

# Проверяем виртуальное окружение
if [ ! -d "venv" ]; then
    echo "📦 Создаём виртуальное окружение..."
    python3 -m venv venv
fi
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt -q

# Проверяем .env
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден! Скопируйте .env.example и заполните значения."
    exit 1
fi

# Применяем миграции
echo "🗄️  Применяем миграции..."
alembic upgrade head

# Запускаем FastAPI
echo "⚡ FastAPI запущен на http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
FASTAPI_PID=$!

# Запускаем Telegram Bot в фоне
echo "🤖 Запускаем Telegram Bot..."
cd "${PROJECT_ROOT}/bot"
python main.py &
BOT_PID=$!

echo ""
echo "✅ AVATAR запущен!"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "Нажмите Ctrl+C для остановки"

# Ждём прерывания
trap "kill $FASTAPI_PID $BOT_PID 2>/dev/null; echo '🛑 Остановлено'" SIGINT SIGTERM
wait
