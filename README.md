# AVATAR — Платформа Эволюции Сознания

> Telegram Mini App для психологического саморазвития через 264 архетипа, шкалу Хокинса и персональный ИИ-ментор.

---

## Быстрый старт

```bash
# 1. Настроить окружение
cp backend/.env.example backend/.env
# Заполни DATABASE_URL, BOT_TOKEN, OPENAI_API_KEY в .env

# 2. Установить зависимости
make install

# 3. Применить миграции
make migrate

# 4. Запустить всё
./run.sh
```

**Frontend** (отдельно):
```bash
cd frontend && npm install && npm run dev
```

---

## Архитектура

AVATAR использует 4-уровневую архитектуру данных:

```
L0 (Ввод) → L1 Rain (расчёты) → L2 River (интерпретация) → L3 Ocean (синтез)
                                                                    ↓
                                               Evolution Layer (хронология)
                                                    ↓           ↓
                                          264 Карты   ←→   Помощник + Аналитика
```

| Уровень | Суть | Основной файл |
|---------|------|---------------|
| L0 | Онбординг (дата/место рождения) | `routers/calc.py` |
| L1 Rain | Swiss Ephemeris + astrologyapi.com | `rro/astro/rain.py` |
| L2 River | LLM синтез 12 сфер | `rro/astro/river.py` |
| L3 Ocean | Алхимический синтез → Identity Passport | `rro/ocean/hub.py` |
| Evolution | Хронология взаимодействий | `services/evolution_service.py` |

📄 Подробнее: [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) · [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md)

---

## Структура проекта

```
AVATARv1.0/
├── backend/
│   └── app/
│       ├── agents/          # AI агенты (assistant, analytics, sync, analytic)
│       ├── core/            # Астрология, экономика, proявление карт
│       ├── models/          # 15 SQLAlchemy моделей
│       ├── routers/         # 15 FastAPI роутеров
│       ├── rro/             # Rain → River → Ocean конвейер
│       └── services/        # EvolutionService, NotificationService
├── bot/                     # aiogram 3.x Telegram Bot
├── frontend/                # Next.js 15 + TypeScript
│   └── src/app/
│       ├── /                # Главная: «Твой AVATAR» + «О тебе» + «Твой мир»
│       ├── /onboarding      # Ввод данных рождения
│       ├── /card/[id]       # Детали архетипа
│       ├── /sync/[id]       # 4-фазная синхронизация
│       └── /diary           # Дневник интеграции
└── docs/                    # 📄 Вся документация
```

---

## Стек технологий

| Слой | Технологии |
|------|-----------|
| Backend | FastAPI, SQLAlchemy async, asyncpg |
| AI | OpenAI o3-mini (синтез), GPT-4o-mini (диалог), text-embedding-3 |
| Астрология | pyswisseph, astrologyapi.com, geopy, timezonefinder |
| Голос | OpenAI Whisper |
| БД | Supabase (PostgreSQL + pgvector) |
| Миграции | Alembic (async) |
| Bot | aiogram 3.x |
| Frontend | Next.js 15, TypeScript, Tailwind CSS, Framer Motion |
| State | Zustand |
| Deploy | Vercel (frontend) + VPS/Timeweb (backend + bot) |

---

## Ключевые API

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/calc` | Онбординг → 264 карты |
| GET | `/api/cards/{uid}` | Все карты пользователя |
| GET | `/api/master-hub/{uid}/about` | «О тебе» (Identity Passport) |
| GET | `/api/master-hub/{uid}/reports` | Еженедельные отчёты |
| POST | `/api/assistant/chat` | Диалог с помощником |
| POST | `/api/analytics/run-daily` | Ежедневный анализ карт |
| POST | `/api/analytics/run-weekly` | Еженедельный отчёт → TG |

📄 Подробнее: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)

---

## Геймификация

| Действие | Награда |
|---------|--------|
| Ежедневный вход | +5–35 ✦ |
| Сессия синхронизации | −25 ✦ |
| Сессия выравнивания | −40 ✦ |
| Запись в дневнике | +25 XP |
| Повышение ранга карты | +100-2000 XP |

📄 Подробнее: [`XP_SYSTEM_GUIDE.md`](XP_SYSTEM_GUIDE.md)

---

## Документация

| Документ | Описание |
|---------|---------|
| [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) | 4-уровневая архитектура с mermaid-диаграммой |
| [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) | Пошаговый конвейер данных |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Все агенты и сервисы |
| [`docs/CARD_SYSTEM.md`](docs/CARD_SYSTEM.md) | 264 карты, статусы, ранги, проявление |
| [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) | 24 таблицы БД |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Полный API Reference |
| [`docs/AI_MODELS_GUIDELINES.md`](docs/AI_MODELS_GUIDELINES.md) | Регламент использования AI моделей |
| [`XP_SYSTEM_GUIDE.md`](XP_SYSTEM_GUIDE.md) | XP, уровни, энергия, ранги |

---

## Разработка

```bash
make dev             # FastAPI с hot-reload
make bot             # Telegram Bot
make frontend        # Next.js dev server
make test            # pytest
make migrate-create  # Создать новую миграцию Alembic
```

## Деплой

```bash
# Frontend → Vercel
npm run deploy:frontend

# Backend + Bot → VPS
expect deploy_vps.exp
```

📄 Подробнее: [`.agents/workflows/deploy.md`](.agents/workflows/deploy.md)

---
*AVATAR v1.0 · Март 2026*
