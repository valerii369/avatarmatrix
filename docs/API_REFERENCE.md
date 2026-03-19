# AVATAR — API Reference

> Base URL (production): `https://avatar.aiguro.pro`  
> Swagger UI: `/docs`

---

## Аутентификация

`POST /api/auth`

Принимает Telegram `initData`, возвращает JWT токен и user object.

```json
Request:  {"init_data": "...telegram initData string..."}
Response: {"token": "...", "user": {"id": 1, "first_name": "...", "onboarding_done": false}}
```

---

## Онбординг и расчёт

### `POST /api/calc/geocode`
Геокодирование места рождения.
```json
Request:  {"birth_place": "Москва, Россия"}
Response: {"lat": 55.75, "lon": 37.62, "tz_name": "Europe/Moscow"}
```

### `POST /api/calc`
Полный расчёт: натальная карта → 264 карты → запуск конвейера Rain→River→Ocean.
```json
Request:  {"user_id": 1, "birth_date": "1990-01-15", "birth_time": "14:30", "birth_place": "Москва, Россия"}
Response: {"success": true, "natal_chart": {...}, "total_cards": 264, "message": "Карта рассчитана. Синтез запущен."}
```

---

## Карты

### `GET /api/cards/{user_id}`
Все 264 карты с текущими статусами и скорами.

### `GET /api/cards/{user_id}/recommended`
Только проявленные карты (RECOMMENDED+).

---

## Паспорт / «О тебе»

### `GET /api/master-hub/{user_id}`
Полный UserPrint (legacy ocean output).

### `GET /api/master-hub/{user_id}/about`
Упрощённые данные для вкладки «О тебе».
```json
Response: {
  "characteristics": {"Ключевая черта": "описание 2-3 предложения"},
  "spheres_brief": {"IDENTITY": "краткое резюме сферы"},
  "has_data": true
}
```

### `GET /api/master-hub/{user_id}/reports`
Еженедельные аналитические отчёты для вкладки «Отчёты».
```json
Response: {
  "reports": [
    {
      "date": "2026-03-17T00:00:00",
      "progress_summary": "...",
      "overall_score": 72,
      "hidden_patterns": ["паттерн 1", "паттерн 2"],
      "critical_points": ["..."],
      "key_insights": ["..."],
      "focus_recommendation": "...",
      "touches_count": 45
    }
  ],
  "has_reports": true
}
```

---

## Синхронизация (Sync)

### `POST /api/sync/start`
Старт сессии синхронизации. Стоимость: 25✦.
```json
Request:  {"user_id": 1, "card_id": 5, "sphere": "IDENTITY"}
Response: {"session_id": 42, "phase": 1, "scene": "Ты стоишь у порога..."}
```

### `POST /api/sync/phase`
Отправить ответ на фазу / получить следующую.
```json
Request:  {"session_id": 42, "user_id": 1, "response": "Я вошёл внутрь"}
Response: {"phase": 2, "scene": "...", "is_complete": false}
```

---

## Цифровой Помощник

### `POST /api/assistant/init`
Начать или продолжить сессию с помощником.
```json
Request:  {"user_id": 1}
Response: {"session_id": 7, "is_first_touch": false}
```

### `POST /api/assistant/chat`
Отправить сообщение помощнику.
```json
Request:  {"user_id": 1, "session_id": 7, "message": "Что значат мои страхи?"}
Response: {
  "ai_response": "Давай разберёмся вместе...",
  "resonance": {"sphere": "TRANSFORMATION", "score": 0.6, "increment": 0.3},
  "discovered_cards": [{"archetype_id": 13, "sphere": "TRANSFORMATION"}]
}
```

### `POST /api/assistant/finish`
Завершить сессию с помощником.
```json
Response: {"status": "session_closed", "diary_summary": "Сессия посвящена теме страха трансформаций..."}
```

---

## Аналитика

### `POST /api/analytics/run-daily`
Ручной триггер ежедневного анализа (обычно cron).
```json
Request:  {"user_id": 1}
Response: {
  "status": "completed",
  "touches_analyzed": 12,
  "sphere_resonances": {"IDENTITY": 1.2, "TRANSFORMATION": 0.8},
  "cards_manifested": [{"archetype_id": 5, "sphere": "IDENTITY", "ai_score": 3.1}],
  "evolution_manifested": []
}
```

### `POST /api/analytics/run-weekly`
Генерация еженедельного отчёта + отправка в Telegram.

### `GET /api/analytics/weekly-report/{user_id}`
Получить все сохранённые отчёты.

---

## Профиль

### `GET /api/profile/{user_id}`
Профиль пользователя: уровень, XP, энергия, фингерпринт.

### `POST /api/profile/tg/{tg_id}/reset`
Полный сброс профиля (для тестов).

---

## Игровые механики

### `GET /api/game/{user_id}`
Игровое состояние: значки, достижения, титулы.

### `POST /api/economy/claim`
Ежедневный сбор энергии.

---

## Дополнительные эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/api/diary/{user_id}` | Дневник интеграции |
| `POST` | `/api/diary` | Новая запись в дневник |
| `GET` | `/api/retro/{user_id}/week` | Недельная ретроспектива |
| `POST` | `/api/voice/transcribe` | Whisper транскрибация |
| `GET` | `/api/profile/{user_id}/referrals` | Список рефералов |
| `GET` | `/health` | Health check |
