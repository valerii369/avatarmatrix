# AVATAR — Платформа Эволюции Сознания

> Telegram Mini App для психологического саморазвития через 264 архетипа, шкалу Хокинса и геймификацию.

## Быстрый старт

```bash
# 1. Клонировать и настроить
cp backend/.env.example backend/.env
# Заполните DATABASE_URL, BOT_TOKEN, OPENAI_API_KEY в .env

# 2. Установить зависимости
make install

# 3. Применить миграции БД
make migrate

# 4. Запустить всё
./run.sh
```

**Frontend** (отдельно):
```bash
cd frontend && npm install && npm run dev
```

## Архитектура

```
AVATARv1.0/
├── backend/
│   ├── app/
│   │   ├── agents/          # OpenAI: master_agent (sync + align + hawkins)
│   │   ├── core/
│   │   │   ├── astrology/   # pyswisseph: natal_chart, aspects, priority_engine
│   │   │   ├── economy.py   # ✦ Энергия, XP, ранги, стрики
│   │   │   └── portrait_builder.py  # Агрегация сессий → рекомендации
│   │   ├── models/          # 14 SQLAlchemy моделей
│   │   ├── routers/         # 12 API роутеров (FastAPI)
│   │   ├── config.py        # pydantic-settings
│   │   ├── database.py      # async SQLAlchemy
│   │   └── main.py          # FastAPI app
│   ├── data/                # 7 JSON файлов данных
│   ├── migrations/          # Alembic async
│   └── tests/               # pytest
├── bot/                     # aiogram 3.x
└── frontend/                # Next.js 15 + TypeScript
    └── src/app/
        ├── /                # Главная (12 сфер + 264 карты)
        ├── /onboarding      # Ввод даты/времени/места рождения
        ├── /card/[id]       # Детали архетипа
        ├── /sync/[id]       # Фазы синхронизации
        ├── /session/[id]    # WebSocket сессия выравнивания
        ├── /diary           # Дневник интеграции
        ├── /profile         # Профиль, XP, осознанность
        └── /reflect         # Ежедневная рефлексия
```

## API Endpoints

| Метод | URL | Описание |
|-------|-----|---------|
| POST | `/api/auth` | Telegram initData → user + token |
| POST | `/api/calc` | Дата рождения → 264 карты |
| GET | `/api/cards/{user_id}` | Все карточки со статусами |
| POST | `/api/sync/start` | Старт синхронизации (25✦) |
| POST | `/api/sync/phase` | Обработка фазы 1-10 |
| WS | `/api/session/{uid}/{card_id}` | Сессия выравнивания (40✦) |
| POST | `/api/reflect` | Ежедневная рефлексия (+10✦) |
| GET | `/api/game/{user_id}` | Игровое состояние |
| GET | `/api/profile/{user_id}` | Профиль + фингерпринт |
| GET | `/api/retro/{user_id}/week` | Недельная ретроспектива |

Swagger UI: `http://localhost:8000/docs`

## Стек технологий

| Слой | Технологии |
|------|-----------|
| Backend | FastAPI, SQLAlchemy (async), asyncpg |
| AI | OpenAI GPT-4o (sync), GPT-4o-mini (hawkins eval) |
| Астрология | pyswisseph, geopy, timezonefinder |
| Голос | OpenAI Whisper |
| БД | Supabase (PostgreSQL) |
| Миграции | Alembic (async) |
| Bot | aiogram 3.x |
| Frontend | Next.js 15, TypeScript, Tailwind CSS, Framer Motion |
| State | Zustand |

## Геймификация

| Действие | Награда |
|---------|--------|
| Вход каждый день | +5–35 ✦ |
| Дневная рефлексия | +10 ✦ |
| Запись в дневнике | +10 ✦ |
| Интеграция плана | +20 ✦ |
| Повышение ранга карты | +25 ✦ |
| Синхронизация (стоит) | −25 ✦ |
| Сессия (стоит) | −40 ✦ |

## Разработка

```bash
make dev       # FastAPI с hot-reload
make bot       # Telegram Bot
make frontend  # Next.js dev server
make test      # pytest
make migrate-create  # Создать новую миграцию
```

## Деплой

Для удобства и предотвращения дубликатов созданы стандартизированные команды:

### Frontend (Vercel)
- **Команда**: `npm run deploy:frontend` (из корня)
- **Что делает**: Переходит в `/frontend` и запускает `vercel deploy --prod` в привязанный проект.

### Backend & Bot (Timeweb / VPS)
- **Команда**: `expect deploy_vps.exp` (из корня)
- **Что делает**: 
  1. Синхронизирует папки `backend/app`, `backend/data`, `bot`.
  2. Перезапускает системные службы `avatar-backend` и `avatar-bot`.
  3. Проверяет статус служб.

*Примечание: Все старые скрипты деплоя перенесены в `scripts/deploy_archive`.*
