# AVATAR — Агенты и сервисы

> Справочник по всем AI-агентам и сервисам системы.

---

## 🤖 AssistantAgent — Цифровой Помощник

**Файл:** `agents/assistant_agent.py`  
**Роутер:** `routers/assistant.py` → `POST /api/assistant/chat`

### Назначение
Персонализированный эмпатичный ментор. Ведёт диалог с пользователем в любое время, помогая осознавать паттерны и двигаться к эволюции. **НЕ** является психологом и **НЕ** ставит диагнозов.

### RAG-контекст (что читает)
1. `IdentityPassport.simplified_characteristics` — 5-7 черт личности
2. `IdentityPassport.spheres_brief` — 12 сфер (кратко)
3. `UserEvolution.touches[-5:]` — последние 5 точек взаимодействия
4. `UserEvolution.session_progress[-3:]` — последние 3 сессии
5. `AssistantSession.final_analysis[-5]` — история прошлых диалогов
6. `CardProgress (ALIGNED/SYNCED/RECOMMENDED)` — активные карты

### Что записывает
- `EvolutionService.record_touch("ASSISTANT_MESSAGE", {...})` — после каждого сообщения
- Резонансный скор (`resonance_scores`) в `AssistantSession`

### Логика проявления карт (в диалоге)
```
resonance_score >= 1.0
  → match_text_to_archetypes(user_message, top_k=3)
  → найденная карта: status = RECOMMENDED, is_recommended_ai = True
  → resonance_scores[sphere] = 0.0 (сброс)
```

---

## 📊 AnalyticsAgent — Аналитический агент (фоновый)

**Файл:** `agents/analytics_agent.py`  
**Роутер:** `routers/analytics.py`

### Назначение
Фоновая аналитика. **Никакого диалога с пользователем**. Занимается исключительно скорингом карт и выявлением паттернов. Запускается ежедневно в 00:00 (или вручную через `/api/analytics/run-daily`).

### Три основных метода

#### `run_daily_analysis(db, user_id)`
```
1. Читает UserEvolution.touches за сегодня
2. Считает resonance по сферам из ASSISTANT_MESSAGE touches
3. match_text_to_archetypes() → top archetype per sphere
4. CardProgress.ai_score += sphere_resonance
5. ai_score >= 3.0 → status = RECOMMENDED, is_recommended_ai = True
```

#### `generate_weekly_report(db, user_id)`
```
1. Читает touches за 7 дней + session_progress
2. LLM анализ → JSON:
   • hidden_patterns, critical_points, key_insights
   • focus_recommendation, overall_score (0-100)
3. Записывает в UserEvolution.evolution_data["weekly_reports"]
4. Отправляет в Telegram (NotificationService)
```

#### `check_evolution_manifestation(db, user_id)`
```
hawkins_peak >= 200 (у SYNCED/ALIGNED карты)
  → unlock следующей LOCKED карты в той же сфере
  → is_recommended_portrait = True
```

---

## 🔍 SyncAgent — Агент синхронизации

**Файл:** `agents/sync_agent.py`  
**Роутер:** `routers/sync.py`

### Назначение
Создаёт проективные сцены для 4-фазной диагностической сессии (ENTRY → DESCENT → SHIFT → INTEGRATION). Каждая фаза — одна сцена с вопросами для рефлексии.

### Контекст (что читает)
- `IdentityPassport` через `PassportService.get_passport_json()` — сферы и характеристики
- Архетип карты (из `ARCHETYPES` dict) и сфера сессии

### Запись результатов
- Фазы → `SyncSession.phases_json`
- Финальный зеркальный анализ → `AnalyticAgent.run_mirror_analysis()` → `AnalyticAgent.update_user_portrait()` → `EvolutionService.update_session_progress()`

---

## 🎭 AnalyticAgent — Зеркальный анализатор

**Файл:** `agents/analytic_agent.py`

### Назначение
Анализирует транскрипт завершённой сессии, извлекает паттерны, символы, телесные якоря, вычисляет Хокинс-скор.

### Ключевые функции

| Функция | Описание |
|---------|----------|
| `run_mirror_analysis()` | Глубокий LLM-анализ транскрипта → `hawkins_score`, `core_pattern`, `shadow_active` |
| `extract_response_features()` | Быстрый разбор ответа на структурированные признаки |
| `update_user_portrait()` | Записывает результат сессии в `EvolutionService.update_session_progress()` |

---

## 🌊 OceanService — Синтетический Алхимик

**Файл:** `rro/ocean/hub.py`

Запускается фоново после завершения `AstroRiver`. Производит L3-синтез и запускает весь downstream конвейер (карты, векторизация).

```
update_ocean()
  → LLM: characteristics + spheres_brief + portrait_summary
  → записывает в IdentityPassport
  → ManifestationService.sync_with_portrait()
  → PassportService.vectorize_passport()
  → db.commit()
```

---

## 🛂 PassportService — Менеджер Паспорта Личности

**Файл:** `rro/passport_service.py`

| Метод | Описание |
|-------|----------|
| `get_or_create(db, uid)` | Получить/создать IdentityPassport |
| `update_channel_data(db, uid, channel, source, data)` | Обновить канал (astrology, matrix...) |
| `get_passport_json(db, uid)` | Получить aggregated_data как dict |
| `vectorize_passport(db, uid)` | Создать/обновить vector_embedding |

---

## 📈 EvolutionService — Трекер эволюции

**Файл:** `services/evolution_service.py`

| Метод | Описание |
|-------|----------|
| `record_touch(db, uid, type, payload)` | Добавить касание в хронологию |
| `record_nn_interaction(db, uid, agent, input, output)` | Лог взаимодействия с агентом |
| `update_session_progress(db, uid, type, data)` | Сохранить прогресс сессии |
| `vectorize_if_needed(db, uid, force)` | Авто-векторизация при update_count >= 10 |

---

## 💎 ManifestationService — Проявление карт

**Файл:** `core/manifest_service.py`

| Лимит | Правило |
|-------|---------|
| IDENTITY | До 3 карт (critical > high) |
| Остальные 11 сфер | До 2 карт (critical > high) |
| Evolution | Если hawkins_peak >= 200 → unlock следующей |
| AI | Если ai_score >= 3.0 → unlock |

Поля при проявлении: `recommendation_source` (`"astro"`, `"evolution"`, `"ai_assistant"`), `manifested_at`
