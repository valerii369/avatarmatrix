# AVATAR — Система Карт (Card System)

> 264 карты = 12 Сфер × 22 Старших Аркана

---

## Концепция

Каждая из 264 карт — это «Ячейка Знания» пользователя. Карта описывает, как конкретный архетип (из 22) проявляется в конкретной жизненной сфере (из 12). Карта эволюционирует вместе с пользователем через сессии синхронизации и выравнивания.

---

## 12 Сфер жизни

| Код | Название |
|-----|----------|
| `IDENTITY` | Личность / Я |
| `RESOURCES` | Ресурсы и материальное |
| `COMMUNICATION` | Коммуникация и разум |
| `ROOTS` | Корни / Семья |
| `CREATIVITY` | Творчество и самовыражение |
| `SERVICE` | Служение и здоровье |
| `PARTNERSHIP` | Отношения |
| `TRANSFORMATION` | Трансформация |
| `EXPANSION` | Расширение и обучение |
| `STATUS` | Статус и карьера |
| `VISION` | Видение и сообщество |
| `SPIRIT` | Дух и интеграция |

---

## Жизненный цикл карты

```
LOCKED → RECOMMENDED → IN_SYNC → SYNCED → ALIGNING → ALIGNED
```

| Статус | Описание |
|--------|----------|
| `LOCKED` | Закрыта. Ещё не проявлена |
| `RECOMMENDED` | Проявлена системой (доступна для входа) |
| `IN_SYNC` | Сессия синхронизации в процессе |
| `SYNCED` | Синхронизация завершена |
| `ALIGNING` | Сессия выравнивания в процессе |
| `ALIGNED` | Полностью проработана |

---

## Источники проявления карт (`recommendation_source`)

### `"astro"` — Астрологическое проявление (онбординг)
Срабатывает после L3-синтеза. Векторный поиск: Shadow/Light/Insight сфер из `IdentityPassport` → cosine similarity → top archetype per sphere.

**Лимиты:**
- IDENTITY: 1-3 карты
- Остальные: 1-2 карты

### `"evolution"` — Эволюционное проявление
Срабатывает при `hawkins_peak >= 200` на любой SYNCED/ALIGNED карте. Автоматически открывает следующую карту в той же сфере по приоритету.

### `"ai_assistant"` — Проявление через помощника
Срабатывает в двух сценариях:
1. **В диалоге**: resonance_score >= 1.0 → `match_text_to_archetypes()` → RECOMMENDED
2. **Ночной анализ**: ai_score >= 3.0 → RECOMMENDED

---

## Ранги карты (Rank)

Ранг растёт по мере прохождения сессий:

| Ранг | Название | Критерий |
|------|----------|----------|
| 0 | Спящий | Только открыта |
| 1 | Пробуждающийся | 1+ сессия |
| 2 | Осознающий | 2+ сессии |
| 3 | Мастер | 5+ сессий |
| 4 | Мудрец | 10+ сессий |
| 5 | Просветлённый | Hawkins >= 500 |

---

## Шкала Хокинса в картах

| Поле | Описание |
|------|----------|
| `hawkins_current` | Текущий уровень (последняя сессия) |
| `hawkins_peak` | Максимум за все сессии |
| `hawkins_min` | Минимум (нижняя точка) |
| `hawkins_entry` | Уровень при первой сессии |

Ключевые пороги:
- **200** → evolution manifestation (разблокировка следующей карты)
- **500** → переход в ранг 5 «Просветлённый»

---

## AI Score

`CardProgress.ai_score` — накопительный скор от AnalyticsAgent.

```
Ежедневно: ai_score += sphere_resonance (из touches)
Порог: ai_score >= 3.0 → карта проявляется
Сброс: после проявления (не сбрасывается, карта уже RECOMMENDED)
```

---

## Векторный матчинг (Avatar Cards)

Каждая из 264 карт в таблице `avatar_cards` имеет `embedding` (1536-мерный вектор от `text-embedding-3-large`). При проявлении:

```python
match_archetypes_to_spheres(sphere_descriptions)
  # Для каждой сферы: 3 вектора (shadow, light, insight)
  # Batch embedding → 1 запрос к OpenAI
  # cosine_distance() в pgvector → top 2 карты per вектор
  # weighted aggregation: shadow×0.4, light×0.4, insight×0.2
  # Winner card → RECOMMENDED
```

---

## Ключевые файлы

| Файл | Роль |
|------|------|
| `models/card_progress.py` | CardProgress model (264 записи per user) |
| `models/avatar_card.py` | AvatarCard — шаблоны карт с embeddings |
| `core/manifest_service.py` | Логика проявления |
| `core/astrology/vector_matcher.py` | Косинусный поиск |
| `core/astrology/priority_engine.py` | Приоритизация карт |
| `routers/cards.py` | GET /api/cards/{user_id} |
