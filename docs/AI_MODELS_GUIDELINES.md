# Регламент использования AI-моделей в AVATAR

> ⛔ **Запрещено** хардкодить названия моделей. Только через `settings`.

---

## Переменные конфигурации (`config.py`)

| Переменная | Текущая модель | Назначение |
|-----------|----------------|-----------|
| `settings.OPENAI_MODEL` | `o3-mini` | Глубокий синтез, аналитика, JSON output |
| `settings.OPENAI_MODEL_FAST` | `gpt-4o-mini` | Быстрые ответы, диалог |
| `text-embedding-3-large` | фиксированно | Векторные embeddings (avatar_cards) |
| `text-embedding-3-small` | фиксированно | Векторизация passport/evolution |
| `whisper-1` | фиксированно | Голос → текст |

> Embedding модели допускается указывать строкой — они являются индустриальным стандартом.

---

## Где используется каждая модель

### `settings.OPENAI_MODEL` (сложный синтез)
- `rro/astro/river.py` — L2 синтез 12 сфер (параллельный)
- `rro/ocean/hub.py` — L3 алхимический синтез
- `agents/analytics_agent.py` — генерация еженедельного отчёта
- `agents/analytic_agent.py` — зеркальный анализ транскрипта

### `settings.OPENAI_MODEL_FAST` (диалог и быстрые задачи)
- `agents/assistant_agent.py` — диалог с Цифровым Помощником
- `agents/sync_agent.py` — генерация фаз синхронизации
- Онбординг-интервью, простые классификации

---

## Правила для разработчиков

```python
# ❌ ЗАПРЕЩЕНО
response = await client.chat.completions.create(model="gpt-4o", ...)

# ✅ ОБЯЗАТЕЛЬНО
from app.agents.common import settings
response = await client.chat.completions.create(model=settings.OPENAI_MODEL, ...)
```

1. **ЗАПРЕЩЕНО** писать `model="gpt-4o"` или `model="o3-mini"` напрямую
2. **ОБЯЗАТЕЛЬНО** импортировать `settings` из `app.config` или `app.agents.common`
3. При добавлении нового агента — обоснуй выбор модели в комментарии к коду
4. Если нужна сверхмощная модель — согласуй с Архитектором, добавь `OPENAI_MODEL_ULTRA` в `config.py`

---

## JSON Output

Для агентов, возвращающих JSON, используй:
```python
response_format={"type": "json_object"}
```
Это гарантирует валидный JSON и снижает вероятность ошибок парсинга.

---
*Последнее обновление: Март 2026*
