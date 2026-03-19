# AVATAR — Схема базы данных

> 24 активные таблицы | База: Supabase (PostgreSQL) | Расширения: pgvector

---

## Основные сущности

### `users`
Ключевая таблица пользователей.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | int PK | Внутренний ID |
| `tg_id` | bigint | Telegram user ID |
| `tg_username` | varchar | Telegram @username |
| `first_name` | varchar | Имя |
| `birth_date` | date | Дата рождения |
| `birth_time` | varchar | Время рождения |
| `birth_place` | varchar | Место рождения |
| `birth_lat/lon/tz` | float/varchar | Геокоординаты |
| `gender` | varchar | Пол |
| `energy` | int | Текущая энергия (✦) |
| `streak` | int | Дней подряд |
| `evolution_level` | int | Уровень эволюции |
| `xp` | int | Накопленный XP |
| `title` | varchar | Текущий титул |
| `onboarding_done` | bool | Пройден онбординг? |
| `referred_by` | int FK | Кто пригласил |
| `referral_code` | varchar | Реферальный код |

---

### `identity_passports` ⭐
Паспорт Личности — единый источник правды. Заполняется конвейером Rain→River→Ocean.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | int FK unique | Один паспорт на пользователя |
| `aggregated_data` | jsonb | L2 данные: `{astrology: {source, data: {spheres: {12 сфер}}}}` |
| `simplified_characteristics` | jsonb | L3: `{«Название черты»: «описание»}` |
| `spheres_brief` | jsonb | L3: `{IDENTITY: «краткое резюме», ...}` |
| `vector_embedding` | vector(1536) | Для RAG семантического поиска |
| `last_vectorized_at` | timestamptz | Когда последний раз векторизовали |

---

### `user_evolutions` ⭐
Хронология эволюции пользователя. Пишется при каждом взаимодействии.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | int FK unique | Один на пользователя |
| `evolution_data` | jsonb | `{touches[], session_progress[], nn_interactions[], weekly_reports[]}` |
| `vector_embedding` | vector(1536) | RAG вектор (обновляется при update_count >= 10) |
| `last_vectorized_at` | timestamptz | |
| `update_count_since_vectorization` | int | Счётчик до авто-векторизации |

---

### `card_progress` ⭐
264 записи на пользователя (12 сфер × 22 архетипа).

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | int FK | |
| `archetype_id` | int | 0-21 |
| `sphere` | varchar | IDENTITY, RESOURCES... |
| `status` | varchar | locked/recommended/in_sync/synced/aligning/aligned |
| `is_recommended_astro` | bool | Проявлена астро-матчингом |
| `is_recommended_portrait` | bool | Проявлена evolution |
| `is_recommended_ai` | bool | Проявлена AI анализом |
| `ai_score` | float | Накопительный AI скор |
| `recommendation_source` | varchar | `"astro"` / `"evolution"` / `"ai_assistant"` |
| `manifested_at` | timestamptz | Дата проявления |
| `hawkins_current` | int | Текущий уровень Хокинса |
| `hawkins_peak` | int | Максимальный Хокинс |
| `hawkins_min` | int | Минимальный Хокинс |
| `hawkins_entry` | int | Уровень при первой сессии |
| `rank` | int | 0-5 |
| `sync_sessions_count` | int | Кол-во sync сессий |
| `align_sessions_count` | int | Кол-во align сессий |
| `astro_priority` | varchar | critical/high/medium/additional |
| `astro_reason` | varchar | Причина приоритета |
| `mental_data` | jsonb | Последний ментальный отпечаток |

---

### `natal_charts`
Результаты астрологических расчётов.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | int FK | |
| `planets_json` | jsonb | Положения планет |
| `aspects_json` | jsonb | Аспекты между планетами |
| `api_raw_json` | jsonb | Сырые данные astrologyapi.com |

---

### `avatar_cards`
Шаблоны карт с векторными embeddings для семантического поиска.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `archetype_id` | int | 0-21 |
| `sphere` | varchar | IDENTITY... |
| `name` | varchar | Название карты |
| `description` | text | Описание |
| `embedding` | vector(1536) | Для cosine_distance поиска |

---

### `sync_sessions`
Сессии синхронизации (4-фазные).

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | int FK | |
| `archetype_id` | int | |
| `sphere` | varchar | |
| `phases_json` | jsonb | Фазы 1-4 с вопросами и ответами |
| `hawkins_score` | int | Финальный скор |
| `core_pattern` | varchar | Извлечённый паттерн |
| `body_anchor` | varchar | Телесный якорь |
| `is_complete` | bool | |

---

### `assistant_sessions`
Сессии диалога с Цифровым Помощником.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | int FK | |
| `messages_json` | jsonb | `[{role, content}]` |
| `resonance_scores` | jsonb | `{IDENTITY: 0.7, ...}` |
| `final_analysis` | jsonb | Дайджест сессии |
| `is_active` | bool | |

---

### `user_prints`
Агрегированный профиль для фронтенда (legacy side-product Ocean).

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | int FK | |
| `print_data` | jsonb | `{portrait_summary, deep_profile_data, metadata}` |

---

## Остальные таблицы

| Таблица | Назначение |
|---------|-----------|
| `align_sessions` | Сессии выравнивания (WebSocket) |
| `ai_diagnostic_sessions` | Голосовые/AI диагностики |
| `diary` | Дневник пользователя |
| `game_state` | Игровое состояние (значки, титулы) |
| `matches` | Матчинг пользователей |
| `daily_reflect` | Ежедневные рефлексии |
| `voice_records` | Голосовые записи (Whisper) |
| `user_memory` | Семантическая память помощника |
| `reflection_sessions` | Сессии рефлексии |
| `events` | Системные события |
| `spheres` | Справочник 12 сфер |
| `archetypes` | Справочник 22 архетипов |
| `user_symbols` | Персональные символы (SymbolicService) |
| `chat_messages` | Сообщения (общий лог) |
| `alembic_version` | Версия миграций |
