# AVATAR — Конвейер данных (Data Pipeline)

> Подробное описание прохождения данных от онбординга до проявления карт.

## Общая схема конвейера

```
Пользователь → L0 → L1 (Rain) → L2 (River → Passport) → L3 (Ocean) → [Карты + Помощник + Аналитика]
```

---

## Шаг 1: Онбординг (L0)

**Триггер:** `POST /api/calc`  
**Файл:** `routers/calc.py`

```python
# Синхронно:
lat, lon, tz_name = await geocode_place(birth_place)     # geopy
natal = await AstroRain.process_onboarding(...)          # Swiss Ephemeris
await db.commit()

# Фоново (background_task):
await run_rro_pipeline(user_id, natal_id)
```

---

## Шаг 2: L1 Rain — Астрологические расчёты

**Файл:** `rro/astro/rain.py`, `rro/astro/api_client.py`  
**БД:** `NatalChart`

```
AstroRain.process_onboarding()
  → pyswisseph: планеты по домам, координаты
  → сохраняет NatalChart.planets_json
  → сохраняет NatalChart.aspects_json

AstroRain.enrich_with_api()
  → astrologyapi.com (ID: 651052)
  → обогащает интерпретациями
  → сохраняет NatalChart.api_raw_json
```

---

## Шаг 3: L2 River — Интерпретация сфер

**Файл:** `rro/astro/river.py`  
**БД:** `IdentityPassport.aggregated_data["astrology"]`

```python
AstroRiver.flow(db, user_id, natal_chart)
  → asyncio.gather(synthesize_deep_sphere × 12)  # параллельно
  → PassportService.update_channel_data(
        channel="astrology",
        data={"spheres": {IDENTITY: {...}, RESOURCES: {...}, ...}}
    )
```

**Структура канала в Passport:**
```json
{
  "astrology": {
    "source": "astrologyapi",
    "data": {
      "spheres": {
        "IDENTITY": {
          "status":           "Архетипический маркер",
          "about":            "В тебе живёт энергия первооткрывателя, который идёт вперёд не оглядываясь. Ты несёшь в себе силу Огня — яркого, прямого, иногда обжигающего. Твоя природа в этой сфере — это вечный поиск собственного лица.",
          "insight":          "Суть сферы в 1-2 предложениях.",
          "light":            "Таланты и высшее предназначение (200-400 зн.)",
          "shadow":           "Страхи, саботаж, слепые пятна (200-400 зн.)",
          "evolutionary_task":"Конкретный духовный урок",
          "life_hacks":       ["Практический шаг 1", "Практический шаг 2"],
          "astrological_markers": ["Планета X в доме Y"],
          "resonance":        85,
          "weighted_resonance":[{"archetype_id": 4, "weight": 90, "reason": "Управитель дома"}]
        },
        "RESOURCES": { "...": "то же самое" },
        "...": "...все 12 сфер"
      }
    }
  }
}
```

> **Расширение**: Для Матрицы Судьбы — создать `rro/matrix/rain.py` + `rro/matrix/river.py` и добавить канал `"matrix"` в Passport.

---

## Шаг 4: L3 Ocean — Алхимический Синтез

**Файл:** `rro/ocean/hub.py`  
**БД:** `IdentityPassport` (simplified_characteristics, spheres_brief, vector_embedding)

```python
OceanService.update_ocean(db, user_id)
  1. Читает IdentityPassport.aggregated_data
  2. LLM (OPENAI_MODEL) → синтез:
       • characteristics: {5-7 черт: "описание 2-3 предложения"}
       • spheres_brief:   L3 генерирует краткое "summary" для каждой сферы
  3. Строит обогащённый spheres_brief: БЕРЁТ ПОЛНЫЙ L2 + добавляет L3 summary
  4. Сохраняет в IdentityPassport
  5. ManifestationService.sync_with_portrait() → карты
  6. PassportService.vectorize_passport() → embedding
  7. db.commit()
```

### Итоговая структура `IdentityPassport.spheres_brief`

Каждая сфера содержит **все поля L2 + поле `summary` из L3**:

```json
{
  "IDENTITY": {
    "status":              "Архетипический маркер (2-4 слова)",
    "about":               "В тебе живёт энергия первооткрывателя... (L2, личностный нарратив)",
    "insight":             "Суть сферы в 1-2 предложениях.",
    "light":               "Таланты и высшее предназначение (200-400 зн.)",
    "shadow":              "Страхи, саботаж, слепые пятна (200-400 зн.)",
    "evolutionary_task":   "Конкретный духовный урок",
    "life_hacks":          ["Практический шаг 1", "Практический шаг 2", "Практический шаг 3"],
    "astrological_markers":["Солнце в Овне в 1-м доме", "Марс квадрат Сатурну"],
    "resonance":           85,
    "weighted_resonance":  [{"archetype_id": 4, "weight": 90, "reason": "Управитель 1-го дома"}],
    "summary":             "Краткое резюме сферы от L3 Алхимика (2-3 предложения)"
  },
  "RESOURCES": { "...": "то же самое — все 10 полей" },
  "...": "...все 12 сфер"
}
```

> **Логика сборки**: `spheres_brief = full_L2_sphere_dict + {"summary": L3_brief}`  
> L3 не перезаписывает L2 — только добавляет `summary` на верхнем уровне.

---

## Шаг 5: Проявление карт

**Файл:** `core/manifest_service.py`, `core/astrology/vector_matcher.py`  
**БД:** `CardProgress` (264 записи = 12 сфер × 22 архетипа)

```
ManifestationService.sync_with_portrait()
  → match_archetypes_to_spheres() — batch embedding (1 OpenAI запрос)
  → параллельный cosine search в avatar_cards по каждой сфере
  → weighted score: Shadow×0.4 + Light×0.4 + Insight×0.2
  
Лимиты при проявлении:
  • IDENTITY: 1-3 карты (приоритет: critical > high)
  • Остальные 11 сфер: 1-2 карты
```

---

## Шаг 6: Evolution — Трекинг взаимодействий

**Файл:** `services/evolution_service.py`  
**БД:** `UserEvolution.evolution_data`

```json
{
  "touches": [
    {"timestamp": "2026-03-19T05:00:00", "type": "ASSISTANT_MESSAGE", "payload": {...}}
  ],
  "session_progress": [
    {"timestamp": "...", "session_type": "sync", "data": {"sphere": "IDENTITY", "hawkins_score": 250}}
  ],
  "nn_interactions": [...],
  "weekly_reports": [...]
}
```

Авто-векторизация: при `update_count_since_vectorization >= 10` → новый `vector_embedding`

---

## Шаг 7: Ежедневный анализ (Midnight Job)

**Файл:** `agents/analytics_agent.py`  
**Триггер:** `POST /api/analytics/run-daily`

```
AnalyticsAgent.run_daily_analysis()
  1. Собирает touches за сегодня из UserEvolution
  2. Считает resonance_score по сферам
  3. match_text_to_archetypes() — vector search
  4. CardProgress.ai_score += score
  5. ai_score >= 3.0 → CardProgress.status = RECOMMENDED
  6. EvolutionService.check_evolution_manifestation()
     → hawkins_peak >= 200 → unlock следующей карты в сфере
```

---

## Шаг 8: Еженедельный отчёт

**Файл:** `routers/analytics.py`  
**Триггер:** `POST /api/analytics/run-weekly`

```
1. Собирает touches за 7 дней
2. LLM → генерирует:
   • hidden_patterns
   • critical_points
   • key_insights
   • focus_recommendation
   • overall_score (0-100)
3. Сохраняет в UserEvolution.evolution_data["weekly_reports"]
4. Отправляет в Telegram
5. Доступен через GET /api/master-hub/{uid}/reports
```
