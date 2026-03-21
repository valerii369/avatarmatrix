# DIGITAL SOUL BLUEPRINT — Полная архитектура системы
## Версия 1.1 | Финальная спецификация

> **Архитектура: 8 учений | Старт: 1 учение (Западная астрология)**

---

## ОГЛАВЛЕНИЕ

1. [Миссия и цель](#1-миссия-и-цель)
2. [Обзор архитектуры (4 слоя)](#2-обзор-архитектуры)
3. [Слой 1 — Raw Calculators](#3-слой-1--raw-calculators)
4. [Слой 2 — Interpretation Engine](#4-слой-2--interpretation-engine)
5. [Слой 3 — Synthesis Oracle](#5-слой-3--synthesis-oracle)
6. [Слой 4 — Vector Portrait Storage](#6-слой-4--vector-portrait-storage)
7. [Формат выходных данных (детальный + краткий)](#7-формат-выходных-данных)
8. [12 сфер портрета](#8-12-сфер-портрета)
9. [Система конвергенции](#9-система-конвергенции)
10. [Система меток влияния](#10-система-меток-влияния)
11. [Книжные RAG-базы](#11-книжные-rag-базы)
12. [Техстек](#12-техстек)
13. [Пайплайн обработки](#13-пайплайн-обработки)
14. [Стоимость и оптимизация](#14-стоимость-и-оптимизация)
15. [Задача для агента-разработчика](#15-задача-для-агента-разработчика)

---

## 1. МИССИЯ И ЦЕЛЬ

### Что строим
Систему **Digital Soul Blueprint** — автономный пайплайн генерации максимально детализированного цифрового портрета личности на основе эзотерических/метафизических учений.

### ⚡ СТРАТЕГИЯ ЗАПУСКА

```
╔══════════════════════════════════════════════════════════════╗
║  АРХИТЕКТУРА: проектируется и строится под ВСЕ 8 УЧЕНИЙ     ║
║  ЗАПУСК:      стартуем с ОДНОГО — Западная астрология       ║
║                                                              ║
║  Все интерфейсы, схемы БД, форматы данных, промпты —        ║
║  универсальные. Подключение нового учения = добавить         ║
║  1 калькулятор + 1 агент. Ядро системы НЕ меняется.         ║
╚══════════════════════════════════════════════════════════════╝
```

**Почему так:**
- Одно учение (астрология) уже даёт ~40-60 факторов на портрет — достаточно для MVP
- Можно сразу проверить качество 5-слойного формата, меток влияния, UX
- Конвергенция (межсистемные совпадения) включается автоматически при подключении 2-го учения
- Каждое новое учение = **инкрементальное обогащение**, не переделка

**Порядок подключения учений:**

| Очередь | Учение | Статус | Когда |
|---------|--------|--------|-------|
| 1 | **Западная астрология** | 🟢 ACTIVE — стартовое учение | MVP |
| 2 | Матрица Судьбы | 🔵 PLANNED — простой калькулятор, быстро подключить | Фаза 2 |
| 3 | Ба Цзы | 🔵 PLANNED | Фаза 2 |
| 4 | Цолькин (Майя) | 🔵 PLANNED — простой калькулятор | Фаза 2 |
| 5 | Нумерология | 🔵 PLANNED | Фаза 2 |
| 6 | Human Design | 🔵 PLANNED — требует API | Фаза 3 |
| 7 | Gene Keys | 🔵 PLANNED — зависит от HD | Фаза 3 |
| 8 | Ведическая астрология | 🔵 PLANNED — сложный калькулятор | Фаза 3 |

### Ключевые принципы
- **Plug-and-play учения:** архитектура поддерживает от 1 до N учений без изменения ядра
- **Без потерь:** каждый фактор из каждого учения должен быть отражён в финальном портрете
- **Изолированная экспертиза:** каждое учение интерпретируется отдельным агентом со своей RAG-базой книг
- **Конвергенция:** система находит где учения сходятся и расходятся (активируется при 2+ учениях)
- **Двойной формат:** детальное описание (5 слоёв) + краткое (1 абзац на сферу)
- **Метки влияния:** каждый фактор помечен уровнем воздействия (высокий/средний/низкий)
- **Векторное хранение:** портрет хранится в pgvector для semantic search агентом-помощником
- **Мировой масштаб:** детализация на уровне, не имеющем аналогов

### Вход
Дата рождения, время рождения, место рождения, ФИО (опционально для нумерологии)

### Выход
Цифровой портрет: 12 сфер × до 15 аспектов × 5 слоёв глубины, с convergence scoring и source stack

### Выход на старте (1 учение — астрология)
Портрет: 12 сфер × 4-10 факторов на сферу × 5 слоёв. Конвергенция = внутрисистемная (аспекты подтверждают друг друга). При подключении 2-го учения — автоматически появляется межсистемная конвергенция.

---

## 2. ОБЗОР АРХИТЕКТУРЫ

```
┌─────────────────────────────────────────────────────────┐
│                    ВХОД: birth_data                      │
│          (дата, время, место, ФИО опционально)           │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              СЛОЙ 1 — RAW CALCULATORS                    │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │🟢Западная│ │⬜Ведическ│ │⬜ Human  │ │⬜ Gene   │   │
│  │ Астролог │ │ Джйотиш │ │  Design  │ │  Keys    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │⬜Нумерол │ │⬜Матрица │ │⬜Ба Цзы  │ │⬜Цолькин │   │
│  │          │ │ Судьбы   │ │          │ │ (Майя)   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                          │
│  🟢 = активен на старте | ⬜ = архитектура готова,       │
│  подключается без изменения ядра                         │
│                                                          │
│  Выход: 1-8 × JSON с сырыми расчётами                   │
│  (на старте: 1 JSON от западной астрологии)              │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           СЛОЙ 2 — INTERPRETATION ENGINE                 │
│                                                          │
│  1-8 специализированных агентов (параллельно)            │
│  На старте: 1 агент (WesternAstrologyAgent)              │
│  Каждый: свой промпт + своя RAG-база книг               │
│  Модель: Claude Sonnet 4.6                               │
│                                                          │
│  Выход: 1-8 × массив Universal Insight Schema            │
│  Каждый insight привязан к сферам 1-12                   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│            СЛОЙ 3 — SYNTHESIS ORACLE                     │
│                                                          │
│  ┌──────────────────────────────────────────┐           │
│  │  MERGER: объединяет все insights по       │           │
│  │  сферам (1 вызов, Sonnet 4.6)            │           │
│  │  Работает одинаково для 1 и 8 учений     │           │
│  └──────────────────┬───────────────────────┘           │
│                     │                                    │
│  ┌──────────────────▼───────────────────────┐           │
│  │  12 × SPHERE AGENT (параллельно)          │           │
│  │  Каждый синтезирует одну сферу            │           │
│  │  Модель: Claude Opus 4.6                  │           │
│  │  Выход: 5 слоёв детализации               │           │
│  │  При 1 учении: Слой 2 (цепочки) =        │           │
│  │  внутрисистемные связи (аспекты между     │           │
│  │  собой). Межсистемная конвергенция        │           │
│  │  появляется при 2+ учениях автоматически  │           │
│  └──────────────────┬───────────────────────┘           │
│                     │                                    │
│  ┌──────────────────▼───────────────────────┐           │
│  │  META AGENT: межсферные суперпаттерны     │           │
│  │  Модель: Claude Opus 4.6                  │           │
│  └──────────────────┬───────────────────────┘           │
│                     │                                    │
│  ┌──────────────────▼───────────────────────┐           │
│  │  COMPRESSOR: генерирует краткий формат    │           │
│  │  из детального (1 вызов, Sonnet 4.6)      │           │
│  └──────────────────────────────────────────┘           │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│         СЛОЙ 4 — VECTOR PORTRAIT STORAGE                 │
│                                                          │
│  Supabase + pgvector                                     │
│                                                          │
│  Схема одинаковая для 1 и 8 учений.                     │
│  Поле source_system отличает данные разных учений.       │
│  При подключении нового учения — новые записи            │
│  добавляются к существующему портрету.                   │
│                                                          │
│  Уровень 1: portrait_facts (атомарные факты)            │
│  Уровень 2: portrait_aspect_chains (цепочки)            │
│  Уровень 3: portrait_patterns (паттерны)                │
│  Уровень 4: portrait_recommendations                    │
│  Уровень 5: portrait_shadow_audit                       │
│  Уровень 6: portrait_meta_patterns                      │
│  Уровень 7: portrait_summary (краткий формат)           │
│                                                          │
│  Все записи с embeddings (vector 1536)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. СЛОЙ 1 — RAW CALCULATORS

### 3.1 Модули расчётов

| # | Модуль | Статус | Вход | Выход | Библиотека/API |
|---|--------|--------|------|-------|----------------|
| 1 | **Западная астрология** | 🟢 ACTIVE | дата, время, место | Натальная карта: планеты в знаках/домах, аспекты, куспиды, стеллиумы, полусферы | Swiss Ephemeris (swisseph) |
| 2 | **Ведическая астрология (Джйотиш)** | ⬜ PLANNED (Фаза 3) | дата, время, место | Раши, накшатры, даши, йоги, навамша | Swiss Ephemeris + Лахири аянамша |
| 3 | **Human Design** | ⬜ PLANNED (Фаза 3) | дата, время, место | Тип, стратегия, авторитет, профиль, определённые центры, каналы, ворота (Personality + Design) | Bodygraph.com API или Jovian Archive API |
| 4 | **Gene Keys** | ⬜ PLANNED (Фаза 3) | дата, время, место | 64 ключа с тенью/даром/сиддхи, Golden Path (Activation, Venus, Pearl Sequence) | Расчёт идентичен HD воротам + линиям, маппинг по таблице Richard Rudd |
| 5 | **Нумерология** | ⬜ PLANNED (Фаза 2) | дата, ФИО | Число судьбы, души, имени, личности, кармические долги, пиннаклы, циклы | Пифагорейская + халдейская, собственный калькулятор |
| 6 | **Матрица Судьбы** | ⬜ PLANNED (Фаза 2) | дата | 22 энергии, карта (центр, комфорт, талант, хвост), линии (денег, отношений, предназначения) | Собственный калькулятор по алгоритму Ладини |
| 7 | **Ба Цзы** | ⬜ PLANNED (Фаза 2) | дата, время, место | 4 столпа (год/месяц/день/час), скрытые стволы, 10 Божеств, баланс 5 стихий, столпы удачи | Китайский солнечный календарь, таблицы Ган Чжи |
| 8 | **Цолькин (Майя)** | ⬜ PLANNED (Фаза 2) | дата | Кин, тон, печать, волна, оракул (аналог, антипод, проводник, скрытый учитель) | Таблица Цолькин 260 кинов, калькулятор по José Argüelles |

> **Принцип plug-and-play:** Каждый модуль реализует единый интерфейс `Calculator.calculate(birth_data) → JSON`. Подключение нового учения = написать класс-наследник + агент интерпретации. Ядро системы (Слои 3-4) **не меняется**.

### 3.2 Формат выхода Слоя 1

Каждый модуль возвращает JSON. Пример (Западная астрология):

```json
{
  "system": "western_astrology",
  "raw_data": {
    "planets": [...],
    "houses": [...],
    "aspects": [...],
    "stelliums": [...],
    "hemispheres": {...}
  },
  "calculated_at": "2026-03-21T12:00:00Z",
  "input_birth_data": {
    "date": "1988-07-02",
    "time": "00:40",
    "place": "Ternopil, Ukraine",
    "timezone": "UTC+4"
  }
}
```

### 3.3 Требования к калькуляторам
- Каждый модуль — изолированный микросервис (Docker контейнер или serverless function)
- Не знает о других модулях
- Идемпотентный: одни и те же входные данные = один и тот же выход
- Время выполнения: < 5 секунд каждый
- Активные модули запускаются **параллельно**
- **Конфигурация активных учений** через переменную окружения или config:
  ```python
  # config.py
  ACTIVE_SYSTEMS = ["western_astrology"]  # На старте только одно
  # При подключении: ["western_astrology", "matrix_of_destiny", "bazi"]
  ```
- Pipeline автоматически запускает только калькуляторы из ACTIVE_SYSTEMS

---

## 4. СЛОЙ 2 — INTERPRETATION ENGINE

### 4.1 Архитектура агента-интерпретатора

Каждое учение обрабатывается **отдельным LLM-агентом** с собственной RAG-базой.

```
┌────────────────────────────────────────┐
│        INTERPRETATION AGENT            │
│                                        │
│  Вход: raw_data JSON из Слоя 1         │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  RAG: поиск по книжной базе      │  │
│  │  (Qdrant / pgvector)             │  │
│  │  → релевантные параграфы         │  │
│  └──────────────┬───────────────────┘  │
│                 │                       │
│  ┌──────────────▼───────────────────┐  │
│  │  LLM (Sonnet 4.6)               │  │
│  │  System prompt:                  │  │
│  │  "Ты эксперт по {учению}.       │  │
│  │  Интерпретируй каждую позицию.   │  │
│  │  Привяжи к сферам 1-12.         │  │
│  │  Выдай в Universal Insight       │  │
│  │  Schema."                        │  │
│  └──────────────┬───────────────────┘  │
│                 │                       │
│  Выход: массив Universal Insight       │
│  Schema, привязанный к сферам          │
└────────────────────────────────────────┘
```

### 4.2 Universal Insight Schema (UIS)

Единый формат выхода для всех 8 агентов:

```json
{
  "id": "uuid",
  "source_system": "western_astrology",
  "position": "Venus retrograde in Aquarius in 10th House",
  "spheres_affected": [1, 7, 10],
  "primary_sphere": 10,
  "influence_level": "high",
  "polarity": "dual",
  "light_aspect": "Способность притягивать ресурсы через нестандартное публичное позиционирование...",
  "shadow_aspect": "Сложные отношения с признанием: хочет его, но не умеет принимать...",
  "energy_description": "Эстетика свободы, ценности сообщества, красота в нетипичных формах...",
  "core_theme": "Переосмысление системы ценностей и отношений",
  "developmental_task": "Найти свою модель признания, не чужую",
  "integration_key": "Принять, что нестандартность — это и есть привлекательность",
  "triggers": ["Ситуации, где нужно соответствовать чужим стандартам красоты/успеха"],
  "timing": "Активируется после 28-30 лет (возврат Сатурна)",
  "book_references": ["Liz Greene:Saturn:p.214", "Howard Sasportas:Twelve Houses:p.187"],
  "confidence": 0.88,
  "weight": 0.85
}
```

### 4.3 Правила для агентов Слоя 2

```
ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:

1. Каждый значимый элемент расчёта ДОЛЖЕН породить минимум один UIS-объект
2. Привязка к сферам: каждый UIS привязан к primary_sphere (основная) 
   и spheres_affected (все затронутые)
3. influence_level: "high" / "medium" / "low" — определяется по:
   - Тесность аспекта / точность позиции
   - Достоинство планеты / сила элемента
   - Центральность для учения (Солнце/Луна = high, астероиды = low)
4. НЕ объединять разные позиции в один UIS — каждая отдельно
5. Использовать ТОЛЬКО книги из своей RAG-базы
6. Язык: конкретный, без обобщений. Не "в целом", а "конкретно"
7. Минимум 3 предложения в light_aspect и shadow_aspect
8. triggers: конкретные жизненные ситуации, не абстракции
```

### 4.4 Модель и параметры

- **Модель:** Claude Sonnet 4.6
- **Temperature:** 0.3 (точность важнее креативности)
- **Max tokens:** 8000 на агента
- **Промпт кэширование:** system prompt + RAG-контент кэшируются

---

## 5. СЛОЙ 3 — SYNTHESIS ORACLE

### 5.1 Компоненты

#### 5.1.1 MERGER (1 вызов)

**Задача:** Принять все UIS-объекты от 8 агентов Слоя 2 и разложить по 12 сферам.

**Модель:** Sonnet 4.6
**Логика:** Чисто механическая сортировка по primary_sphere + дедупликация

**Выход:**
```json
{
  "sphere_1": [UIS_1, UIS_2, UIS_3, ...],
  "sphere_2": [UIS_4, UIS_5, ...],
  ...
  "sphere_12": [UIS_n, ...]
}
```

#### 5.1.2 SPHERE AGENTS (12 вызовов, параллельно)

**Задача:** Каждый агент получает ВСЕ UIS-объекты одной сферы от ВСЕХ учений и генерирует **5 слоёв детализации**.

**Модель:** Claude Opus 4.6
**Temperature:** 0.4
**Max tokens:** 12000 на сферу

**System prompt для Sphere Agent:**

```
Ты — Synthesis Oracle. Получаешь факторы из 8 учений для ОДНОЙ сферы жизни.

ТВОЯ ЗАДАЧА:
Сгенерировать 5 слоёв детализации для этой сферы.

СЛОЙ 1 — АТОМАРНЫЕ ФАКТОРЫ:
- Каждый входной UIS = отдельный фактор
- Каждый фактор расписан подробно (5-10 предложений)
- Указан источник (учение) и influence_level
- НИЧЕГО не выбрасывать. Каждый UIS отражён

СЛОЙ 2 — АСПЕКТНЫЕ ЦЕПОЧКИ:
- Найди связи МЕЖДУ факторами из РАЗНЫХ учений
- Если 2+ учения указывают на одно — это цепочка
- Укажи convergence_score (0.0-1.0)
- Формат: Фактор A (система X) + Фактор B (система Y) = вывод

СЛОЙ 3 — СИНТЕЗИРОВАННЫЕ ПАТТЕРНЫ:
- Объедини цепочки в 3-7 ключевых паттернов сферы
- Каждый паттерн: название + формула + подробное описание
- Укажи какие системы поддерживают каждый паттерн

СЛОЙ 4 — РЕКОМЕНДАЦИИ:
- Конкретные, практические рекомендации (5-15 штук)
- Каждая с источником (какое учение) и influence_level
- Формат: рекомендация + источник + уровень влияния

СЛОЙ 5 — ТЕНЕВОЙ АУДИТ:
- Риски, ловушки, слепые зоны (3-10 штук)
- Каждый с convergence_score + антидотом
- Чем выше convergence — тем серьёзнее риск

ПРАВИЛА:
1. Каждый входной фактор ОБЯЗАН появиться в Слое 1
2. Не пиши "в целом" или "в общем" — только конкретика
3. Если учения противоречат — создай аспект "Парадокс" в Слое 2
4. influence_level: 🔴 HIGH / 🟡 MEDIUM / 🟢 LOW
5. convergence_score: процент учений, подтверждающих вывод
6. Минимум 6 факторов в Слое 1, минимум 3 цепочки в Слое 2
7. Язык: живой, конкретный, с примерами ситуаций
```

#### 5.1.3 META AGENT (1 вызов, после всех Sphere Agents)

**Задача:** Найти межсферные суперпаттерны — "красные нити", пронизывающие несколько сфер.

**Модель:** Claude Opus 4.6
**Вход:** Все 12 синтезированных сфер (Слой 3 от каждого Sphere Agent)

**Выход:**
```json
{
  "meta_patterns": [
    {
      "name": "Строитель нового мировоззрения",
      "spheres_involved": [9, 10, 11, 12],
      "description": "...",
      "convergence_score": 0.92,
      "systems_supporting": ["astrology", "bazi", "tzolkin"],
      "embedding": [...]
    }
  ]
}
```

#### 5.1.4 COMPRESSOR (1 вызов)

**Задача:** Сгенерировать КРАТКИЙ формат портрета из детального.

**Модель:** Sonnet 4.6
**Правило:** 1 абзац (3-5 предложений) на сферу. Только самое важное. Без потери сути.

**Выход:**
```json
{
  "sphere_1_brief": "Ты — гора с чувственной оболочкой...",
  "sphere_2_brief": "Деньги приходят через голос и технологии...",
  ...
  "overall_brief": "3-5 предложений о человеке в целом"
}
```

---

## 6. СЛОЙ 4 — VECTOR PORTRAIT STORAGE

### 6.1 Схема базы данных (Supabase)

```sql
-- Основная таблица портрета
CREATE TABLE digital_portraits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  birth_data JSONB NOT NULL,
  status TEXT DEFAULT 'generating', -- generating | ready | error
  version INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Уровень 1: Атомарные факты (из Слоя 2)
CREATE TABLE portrait_facts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portrait_id UUID REFERENCES digital_portraits(id) ON DELETE CASCADE,
  source_system TEXT NOT NULL, -- western_astrology, bazi, human_design, etc.
  sphere_primary INTEGER NOT NULL CHECK (sphere_primary BETWEEN 1 AND 12),
  spheres_affected INTEGER[] DEFAULT '{}',
  position TEXT NOT NULL, -- "Venus retrograde in Aquarius in 10H"
  influence_level TEXT NOT NULL CHECK (influence_level IN ('high', 'medium', 'low')),
  light_aspect TEXT,
  shadow_aspect TEXT,
  energy_description TEXT,
  core_theme TEXT,
  developmental_task TEXT,
  triggers TEXT[],
  timing TEXT,
  book_references TEXT[],
  weight FLOAT DEFAULT 0.5,
  confidence FLOAT DEFAULT 0.5,
  raw_uis JSONB, -- полный Universal Insight Schema
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Уровень 2: Аспектные цепочки (межсистемные связи)
CREATE TABLE portrait_aspect_chains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portrait_id UUID REFERENCES digital_portraits(id) ON DELETE CASCADE,
  sphere INTEGER NOT NULL,
  chain_name TEXT NOT NULL,
  factors_involved UUID[], -- ссылки на portrait_facts.id
  systems_involved TEXT[],
  convergence_score FLOAT NOT NULL CHECK (convergence_score BETWEEN 0 AND 1),
  description TEXT NOT NULL,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Уровень 3: Синтезированные паттерны
CREATE TABLE portrait_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portrait_id UUID REFERENCES digital_portraits(id) ON DELETE CASCADE,
  sphere INTEGER NOT NULL,
  pattern_name TEXT NOT NULL,
  formula TEXT, -- краткая формула паттерна
  description TEXT NOT NULL,
  systems_supporting TEXT[],
  convergence_score FLOAT,
  influence_level TEXT CHECK (influence_level IN ('high', 'medium', 'low')),
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Уровень 4: Рекомендации
CREATE TABLE portrait_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portrait_id UUID REFERENCES digital_portraits(id) ON DELETE CASCADE,
  sphere INTEGER NOT NULL,
  recommendation TEXT NOT NULL,
  source_systems TEXT[],
  influence_level TEXT CHECK (influence_level IN ('high', 'medium', 'low')),
  category TEXT, -- practical, mindset, timing, partnership, etc.
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Уровень 5: Теневой аудит
CREATE TABLE portrait_shadow_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portrait_id UUID REFERENCES digital_portraits(id) ON DELETE CASCADE,
  sphere INTEGER NOT NULL,
  risk_name TEXT NOT NULL,
  description TEXT NOT NULL,
  source_systems TEXT[],
  convergence_score FLOAT,
  antidote TEXT NOT NULL,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Уровень 6: Межсферные суперпаттерны (от Meta Agent)
CREATE TABLE portrait_meta_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portrait_id UUID REFERENCES digital_portraits(id) ON DELETE CASCADE,
  pattern_name TEXT NOT NULL,
  spheres_involved INTEGER[],
  description TEXT NOT NULL,
  systems_supporting TEXT[],
  convergence_score FLOAT,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Уровень 7: Краткий формат (от Compressor)
CREATE TABLE portrait_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portrait_id UUID REFERENCES digital_portraits(id) ON DELETE CASCADE,
  sphere INTEGER, -- NULL для overall
  brief_text TEXT NOT NULL,
  is_overall BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Индексы для vector search
CREATE INDEX idx_facts_embedding ON portrait_facts 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chains_embedding ON portrait_aspect_chains 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_patterns_embedding ON portrait_patterns 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_recommendations_embedding ON portrait_recommendations 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_shadow_embedding ON portrait_shadow_audit 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_meta_embedding ON portrait_meta_patterns 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);

-- Стандартные индексы
CREATE INDEX idx_facts_portrait ON portrait_facts(portrait_id);
CREATE INDEX idx_facts_sphere ON portrait_facts(sphere_primary);
CREATE INDEX idx_facts_system ON portrait_facts(source_system);
CREATE INDEX idx_facts_influence ON portrait_facts(influence_level);
```

### 6.2 Embedding стратегия

Для каждой записи embedding генерируется из конкатенации ключевых полей:

```python
def generate_embedding_text(record):
    """Формирует текст для embedding из записи."""
    parts = [
        f"Сфера: {SPHERE_NAMES[record.sphere]}",
        f"Тема: {record.core_theme or record.pattern_name or record.risk_name}",
        f"Описание: {record.description or record.light_aspect}",
        f"Тень: {record.shadow_aspect or ''}",
        f"Рекомендация: {record.recommendation or record.antidote or ''}"
    ]
    return " | ".join([p for p in parts if p.split(": ")[1]])
```

---

## 7. ФОРМАТ ВЫХОДНЫХ ДАННЫХ

### 7.1 Детальный формат ("О тебе" — полный)

Для каждой сферы — 5 слоёв:

```
СФЕРА N — [НАЗВАНИЕ]

═══ СЛОЙ 1: АТОМАРНЫЕ ФАКТОРЫ ═══

ФАКТОР 1: [название] ([учение])
Влияние: 🔴 ВЫСОКОЕ / 🟡 СРЕДНЕЕ / 🟢 НИЗКОЕ
[Подробное описание: 5-15 предложений]
Свет: [...]
Тень: [...]
Триггеры: [...]

ФАКТОР 2: ...
[повторяется для каждого фактора, 6-20 штук на сферу]

═══ СЛОЙ 2: АСПЕКТНЫЕ ЦЕПОЧКИ ═══

ЦЕПОЧКА A: "[название]"
Convergence: 0.XX | Системы: [список]
[описание связи между факторами из разных учений]

═══ СЛОЙ 3: СИНТЕЗИРОВАННЫЕ ПАТТЕРНЫ ═══

ПАТТЕРН 1: "[название]"
Формула: [краткая формула]
Convergence: 0.XX | Системы: [список]
[подробное описание]

═══ СЛОЙ 4: РЕКОМЕНДАЦИИ ═══

| # | Рекомендация | Источник | Влияние |
|---|---|---|---|
| 1 | [...] | [...] | 🔴/🟡/🟢 |

═══ СЛОЙ 5: ТЕНЕВОЙ АУДИТ ═══

| Риск | Convergence | Источники | Антидот |
|---|---|---|---|
| [...] | 0.XX | [...] | [...] |
```

### 7.2 Краткий формат ("О тебе" — короткий)

Для каждой сферы — 1 абзац (3-5 предложений), содержащий:
- Ядро сферы (1 предложение)
- Главный свет (1 предложение)
- Главная тень (1 предложение)
- Ключевая рекомендация (1 предложение)

Пример:
> **Деньги:** Ты — гора золота с замедленным зажиганием. Зарабатываешь через голос, информацию и технологии. Доход цикличен — это нормально, не баг. Пик после 38-40. Строй автономные системы, а не меняй время на зарплату.

---

## 8. 12 СФЕР ПОРТРЕТА

| # | Сфера | Ключевые темы | Астро-дом |
|---|-------|---------------|-----------|
| 1 | **Идентичность / Я** | Кто ты в ядре, архетип, тип энергии, маска vs суть | 1 |
| 2 | **Ресурсы / Деньги / Ценности** | Финансы, самооценка, что ценишь, как зарабатываешь | 2 |
| 3 | **Коммуникация / Мышление** | Стиль мысли, речь, обучение, ближний круг | 3 |
| 4 | **Корни / Семья / Безопасность** | Род, семья, дом, эмоциональный фундамент | 4 |
| 5 | **Творчество / Самовыражение** | Креативность, дети, романтика, игра, радость | 5 |
| 6 | **Здоровье / Рутина / Служение** | Тело, ежедневная практика, работа, полезность | 6 |
| 7 | **Отношения / Партнёрство** | Личные и деловые партнёрства, притяжения, проекции | 7 |
| 8 | **Трансформация / Глубина** | Кризисы, чужие ресурсы, сексуальность, перерождение | 8 |
| 9 | **Мировоззрение / Экспансия** | Философия, путешествия, образование, вера | 9 |
| 10 | **Призвание / Реализация** | Карьера, миссия, статус, жизненный путь | 10 |
| 11 | **Сообщество / Будущее** | Друзья, группы, мечты, коллективная роль | 11 |
| 12 | **Бессознательное / Духовность** | Скрытые программы, медитация, уединение | 12 |

### 8.1 Маппинг учений на сферы

Каждое учение вносит вклад в разные сферы:

| Учение | Основной вклад в сферы |
|--------|----------------------|
| Западная астрология | Все 12 (через дома и планеты) |
| Ведическая астрология | Все 12 (через бхавы и накшатры) |
| Human Design | 1, 3, 5, 6, 7, 10, 11 (через типы, центры, каналы) |
| Gene Keys | 1, 5, 7, 8, 10, 12 (через последовательности) |
| Нумерология | 1, 2, 4, 5, 7, 10 (через числовые позиции) |
| Матрица Судьбы | 1, 2, 4, 7, 8, 10, 12 (через линии энергий) |
| Ба Цзы | 1, 2, 4, 7, 10 (через столпы и 10 Божеств) |
| Цолькин | 1, 5, 9, 10, 12 (через кин, печать, тон) |

---

## 9. СИСТЕМА КОНВЕРГЕНЦИИ

### 9.1 Что такое конвергенция

Конвергенция — это мера согласия между учениями. Когда 4 из 8 систем указывают на одну тему в одной сфере — это высокая конвергенция.

**Поведение при разном количестве учений:**

| Учений | Тип конвергенции | Пример |
|--------|-----------------|--------|
| **1 (старт)** | Внутрисистемная | "Солнце в Козероге + Сатурн в обители + MC в Козероге → все указывают на карьеру через структуру" |
| **2-3** | Межсистемная (базовая) | "Астрология: Меркурий управляет деньгами + Ба Цзы: дефицит Металла → оба указывают на tech как источник дохода" |
| **4-8** | Межсистемная (полная) | "5 из 8 систем указывают на позднее раскрытие потенциала → convergence 0.92" |

При 1 учении система работает полноценно — просто convergence считается между ЭЛЕМЕНТАМИ одного учения (планеты подтверждают друг друга, аспекты формируют паттерны). При добавлении 2-го учения — автоматически появляется межсистемная конвергенция без изменения кода.

### 9.2 Формула расчёта

```python
def calculate_convergence(insights_for_theme: list, active_systems: list) -> float:
    """
    insights_for_theme: список UIS-объектов, указывающих на одну тему
    active_systems: список активных учений (от 1 до 8)
    """
    unique_systems = set(i.source_system for i in insights_for_theme)
    total_systems = len(active_systems)  # динамически: 1 на старте, 8 в полной версии
    
    if total_systems == 1:
        # При 1 учении: convergence = количество подтверждающих факторов / общее
        # Чем больше элементов одного учения указывают на тему — тем выше score
        factor_count = len(insights_for_theme)
        base_score = min(1.0, factor_count / 5)  # 5+ факторов = 1.0
    else:
        # При 2+ учениях: convergence = процент систем
        base_score = len(unique_systems) / total_systems
    
    # Бонус за тесные аспекты / точные позиции
    weight_bonus = sum(i.weight for i in insights_for_theme) / len(insights_for_theme)
    
    # Финальный счёт (0.0 - 1.0)
    convergence = min(1.0, base_score * 0.7 + weight_bonus * 0.3)
    
    return round(convergence, 2)
```

### 9.3 Уровни конвергенции

| Счёт | Уровень | Значение |
|------|---------|----------|
| 0.85 - 1.00 | 🔴 Критическая | 5+ систем сходятся — это определяющая черта |
| 0.60 - 0.84 | 🟡 Значительная | 3-4 системы сходятся — важная тема |
| 0.30 - 0.59 | 🟢 Умеренная | 2 системы сходятся — заслуживает внимания |
| 0.00 - 0.29 | ⚪ Единичная | Только 1 система — фоновый фактор |

### 9.4 Парадоксы (противоречия между системами)

Когда учения **противоречат** друг другу — это не ошибка, а **отдельный тип данных**.

```json
{
  "type": "paradox",
  "sphere": 2,
  "system_a": "bazi",
  "says_a": "Сильная Земля = прагматизм, осторожность",
  "system_b": "matrix",
  "says_b": "Энергия 2 (Жрица) = интуитивные решения",
  "resolution": "Два инструмента: интуиция выбирает 'что', прагматизм строит 'как'",
  "convergence_score": 0.0
}
```

---

## 10. СИСТЕМА МЕТОК ВЛИЯНИЯ

### 10.1 Уровни влияния

Каждый факт, цепочка, паттерн и рекомендация маркируются уровнем влияния:

| Метка | Символ | Критерии |
|-------|--------|----------|
| **HIGH** | 🔴 | Управитель дома / День-Мастер / Точный аспект (орб < 2°) / Доминанта карты / Основная печать/тон / Центральная энергия Матрицы / Определённый канал HD |
| **MEDIUM** | 🟡 | Аспекты 2-5° / Скрытые стволы / Второстепенные позиции / Вспомогательные элементы оракула / Побочные энергии Матрицы |
| **LOW** | 🟢 | Широкие аспекты (5-10°) / Поколенческие планеты без личных аспектов / Фоновые элементы / Дополнительные указатели |

### 10.2 Как метки используются

- В UI: пользователь может фильтровать "показать только HIGH"
- В агенте-помощнике: при ответе на вопрос приоритизирует HIGH факторы
- В рекомендациях: HIGH-рекомендации подаются первыми

---

## 11. КНИЖНЫЕ RAG-БАЗЫ

### 11.1 Структура хранения

Каждое учение — отдельная коллекция в Qdrant / pgvector.

```
collections/
├── western_astrology/
│   ├── arroyo_chart_interpretation.chunks
│   ├── hand_planets_in_transit.chunks
│   ├── greene_saturn.chunks
│   ├── sasportas_twelve_houses.chunks
│   └── ...
├── vedic_astrology/
│   ├── raman_how_to_judge.chunks
│   ├── parashara_hora_shastra.chunks
│   └── ...
├── human_design/
│   ├── ra_uru_hu_definitive_book.chunks
│   ├── bunnell_definitive_book.chunks
│   ├── parkyn_discover_person.chunks
│   └── ...
├── gene_keys/
│   ├── rudd_gene_keys.chunks
│   ├── rudd_art_contemplation.chunks
│   ├── golden_path_materials.chunks
│   └── ...
├── numerology/
│   ├── millman_life_born_to_live.chunks
│   ├── decoz_numerology.chunks
│   └── ...
├── matrix_of_destiny/
│   ├── ladini_methodology.chunks
│   ├── arcana_crowley_interpretations.chunks
│   └── ...
├── bazi/
│   ├── king_destiny_code.chunks
│   ├── chung_good_fortune.chunks
│   └── ...
└── tzolkin/
    ├── arguelles_mayan_factor.chunks
    ├── spilsbury_mayan_oracle.chunks
    └── ...
```

### 11.2 Список книг по учениям

#### Западная астрология
1. Stephen Arroyo — "Chart Interpretation Handbook"
2. Stephen Arroyo — "Astrology, Psychology & the Four Elements"
3. Robert Hand — "Planets in Transit"
4. Robert Hand — "Horoscope Symbols"
5. Liz Greene — "Saturn: A New Look at an Old Devil"
6. Liz Greene — "The Astrology of Fate"
7. Howard Sasportas — "The Twelve Houses"
8. Dane Rudhyar — "The Astrology of Personality"

#### Ведическая астрология
1. B.V. Raman — "How to Judge a Horoscope" (vol 1-2)
2. K.N. Rao — серия по Джйотиш
3. Parashara — "Brihat Parashara Hora Shastra"
4. Ernst Wilhelm — "Graha Sutras"

#### Human Design
1. Ra Uru Hu — "The Definitive Book of Human Design"
2. Lynda Bunnell — "The Definitive Book of HD" (practical)
3. Chetan Parkyn — "Human Design: Discover the Person You Were Born to Be"
4. Karen Curry Parker — "Understanding Human Design"

#### Gene Keys
1. Richard Rudd — "Gene Keys: Unlocking the Higher Purpose Hidden in Your DNA"
2. Richard Rudd — "The Art of Contemplation"
3. Golden Path / Venus Sequence / Pearl Sequence materials

#### Нумерология
1. Dan Millman — "The Life You Were Born to Live"
2. Hans Decoz — "Numerology: Key To Your Inner Self"
3. Faith Javane & Dusty Bunker — "Numerology and the Divine Triangle"

#### Матрица Судьбы
1. Наталья Ладини — базовая методология 22 энергий
2. Маппинг Арканов по школам Кроули / Уэйта / Марсельской

#### Ба Цзы
1. Jerry King — "Bazi: The Destiny Code"
2. Lily Chung — "The Path to Good Fortune"
3. Joey Yap — "Bazi: The Destiny Code Revealed"

#### Цолькин
1. José Argüelles — "The Mayan Factor"
2. Ariel Spilsbury — "The Mayan Oracle"
3. Eden Sky — "13 Moon Almanac" materials

### 11.3 Правила чанкинга

- Chunk size: 500-800 токенов
- Overlap: 100 токенов
- Метаданные каждого чанка: book, chapter, page, topic_keywords
- Top-K retrieval: 5-8 чанков на запрос агента

---

## 12. ТЕХСТЕК

### 12.1 Основной стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| LLM API | Anthropic Claude API (Opus 4.6 + Sonnet 4.6) |
| Vector DB | Supabase pgvector (основной) + Qdrant (RAG книг) |
| Database | Supabase PostgreSQL |
| Queue | Redis + Celery (оркестрация параллельных вызовов) |
| Embedding | OpenAI text-embedding-3-small (1536 dims) |
| Orchestration | n8n (high-level) или Python native (low-level) |
| Hosting | Docker + Timeweb VPS / AWS |
| Frontend | Next.js 14 + React + Framer Motion |
| Auth | Supabase Auth |

### 12.2 Порядок приоритетов разработки

```
ФАЗА 1 — MVP: Одно учение, полный цикл (2-3 недели):
  ☐ Базовые классы (Calculator, InterpretationAgent, UIS schema)
  ☐ Config: ACTIVE_SYSTEMS = ["western_astrology"]
  ☐ Калькулятор западной астрологии (swisseph)
  ☐ 1 агент интерпретации (WesternAstrologyAgent)
  ☐ Merger + 12 Sphere Agents + Meta Agent + Compressor (Слой 3)
  ☐ Supabase схема (полная, под все учения)
  ☐ Сохранение + embeddings
  ☐ API endpoints (полный набор)
  ☐ Минимальный UI: ввод → ожидание → портрет (детальный + краткий)
  ☐ Тестирование на 5+ картах

ФАЗА 2 — Простые учения (2-3 недели):
  ☐ Калькулятор Матрицы Судьбы + агент
  ☐ Калькулятор Ба Цзы + агент
  ☐ Калькулятор Цолькин + агент
  ☐ Калькулятор Нумерологии + агент
  ☐ Конвергенция включается автоматически (2+ систем)
  ☐ RAG-базы книг (Qdrant) для всех активных учений

ФАЗА 3 — Сложные учения + оптимизация (2-3 недели):
  ☐ Human Design (API интеграция)
  ☐ Gene Keys (маппинг из HD)
  ☐ Ведическая астрология (swisseph + Лахири)
  ☐ Prompt caching + Batch API
  ☐ Агент-помощник (чат с semantic search по портрету)
  ☐ UI: convergence визуализация, фильтры по influence_level

ФАЗА 4 — Масштабирование:
  ☐ Автоскейлинг воркеров
  ☐ Кэширование портретов
  ☐ Перегенерация портрета при подключении нового учения
  ☐ Мультиязычность
  ☐ Административная панель
```

---

## 13. ПАЙПЛАЙН ОБРАБОТКИ

### 13.1 Полный flow

```python
async def generate_portrait(birth_data: BirthData) -> Portrait:
    """Генерация полного портрета — end-to-end pipeline.
    Работает одинаково для 1 и 8 учений.
    Количество активных учений определяется ACTIVE_SYSTEMS config.
    """
    
    active_calculators = get_active_calculators()  # из config
    # На старте: [WesternAstrologyCalculator]
    # Позже:     [WesternAstrology, Matrix, Bazi, Tzolkin, ...]
    
    # ═══ СЛОЙ 1: Расчёты (параллельно) ═══
    raw_results = await asyncio.gather(*[
        calc.calculate(birth_data) for calc in active_calculators
    ])
    # На старте (1 учение): ~2 сек
    # Полная система (8 учений): ~5 сек (параллельно)
    
    # ═══ СЛОЙ 2: Интерпретация (параллельно) ═══
    active_agents = get_active_agents()  # 1:1 с калькуляторами
    interpretations = await asyncio.gather(*[
        agent.interpret(raw_data=raw)
        for agent, raw in zip(active_agents, raw_results)
    ])
    # На старте (1 агент): ~8-12 сек
    # Полная система (8 агентов): ~12-15 сек (параллельно)
    
    # ═══ СЛОЙ 3a: Merger ═══
    all_insights = flatten(interpretations)
    spheres_data = await merge_by_spheres(
        insights=all_insights,
        model="claude-sonnet-4-6"
    )
    # ~3-5 сек (не зависит от количества учений)
    
    # ═══ СЛОЙ 3b: 12 Sphere Agents (параллельно) ═══
    sphere_portraits = await asyncio.gather(*[
        synthesize_sphere(
            sphere_num=i,
            sphere_insights=spheres_data[f"sphere_{i}"],
            active_systems=ACTIVE_SYSTEMS,  # передаём список для адаптации промпта
            model="claude-opus-4-6"
        )
        for i in range(1, 13)
    ])
    # ~15-25 сек (параллельно)
    
    # ═══ СЛОЙ 3c: Meta Agent ═══
    meta_patterns = await find_meta_patterns(
        all_spheres=sphere_portraits,
        model="claude-opus-4-6"
    )
    # ~5-10 сек
    
    # ═══ СЛОЙ 3d: Compressor ═══
    brief_portrait = await compress_portrait(
        detailed=sphere_portraits,
        meta=meta_patterns,
        model="claude-sonnet-4-6"
    )
    # ~3-5 сек
    
    # ═══ СЛОЙ 4: Сохранение + Embedding ═══
    portrait_id = await save_portrait(
        facts=all_insights,
        spheres=sphere_portraits,
        meta=meta_patterns,
        brief=brief_portrait,
        birth_data=birth_data,
        systems_used=ACTIVE_SYSTEMS  # сохраняем какие учения использованы
    )
    
    await generate_and_save_embeddings(portrait_id)
    
    # ═══ ИТОГО ═══
    # 1 учение (MVP):     ~35-55 секунд
    # 8 учений (полная):  ~45-70 секунд
    # Разница минимальна благодаря параллелизации
    
    return portrait_id
```

### 13.2 Количество LLM-вызовов на портрет

**На старте (1 учение):**

| Этап | Вызовов | Модель | Параллельно |
|------|---------|--------|-------------|
| Слой 2: Интерпретация | 1 | Sonnet 4.6 | — |
| Слой 3a: Merger | 1 | Sonnet 4.6 | — |
| Слой 3b: Sphere Agents | 12 | Opus 4.6 | Да |
| Слой 3c: Meta Agent | 1 | Opus 4.6 | — |
| Слой 3d: Compressor | 1 | Sonnet 4.6 | — |
| **ИТОГО** | **16** | — | — |

**Полная система (8 учений):**

| Этап | Вызовов | Модель | Параллельно |
|------|---------|--------|-------------|
| Слой 2: Интерпретация | 8 | Sonnet 4.6 | Да |
| Слой 3a: Merger | 1 | Sonnet 4.6 | — |
| Слой 3b: Sphere Agents | 12 | Opus 4.6 | Да |
| Слой 3c: Meta Agent | 1 | Opus 4.6 | — |
| Слой 3d: Compressor | 1 | Sonnet 4.6 | — |
| **ИТОГО** | **23** | — | — |

### 13.3 Последовательность выполнения

**На старте (1 учение):**
```
[Последоват.] Слой 1: 1 калькулятор        → ~2 сек
     ↓
[Последоват.] Слой 2: 1 интерпретатор      → ~10 сек
     ↓
[Последоват.] Слой 3a: Merger               → ~4 сек
     ↓
[Параллельно] Слой 3b: 12 Sphere Agents    → ~20 сек
     ↓
[Последоват.] Слой 3c: Meta Agent           → ~8 сек
     ↓
[Последоват.] Слой 3d: Compressor           → ~4 сек
     ↓
[Последоват.] Слой 4: Сохранение            → ~7 сек
                                      ИТОГО: ~55 сек
```

**Полная система (8 учений):**
```
[Параллельно] Слой 1: 8 калькуляторов      → ~3 сек
     ↓
[Параллельно] Слой 2: 8 интерпретаторов    → ~15 сек
     ↓
[Последоват.] Слой 3a: Merger               → ~5 сек
     ↓
[Параллельно] Слой 3b: 12 Sphere Agents    → ~25 сек
     ↓
[Последоват.] Слой 3c: Meta Agent           → ~8 сек
     ↓
[Последоват.] Слой 3d: Compressor           → ~4 сек
     ↓
[Последоват.] Слой 4: Сохранение            → ~10 сек
                                      ИТОГО: ~70 сек
```

---

## 14. СТОИМОСТЬ И ОПТИМИЗАЦИЯ

### 14.1 Стоимость за 1 портрет

**На старте (1 учение — западная астрология):**

| Компонент | Input tokens | Output tokens | Модель | Стоимость |
|-----------|-------------|---------------|--------|-----------|
| 1 × Интерпретация | ~10K | ~5K | Sonnet $3/$15 | ~$0.11 |
| 1 × Merger | ~8K | ~4K | Sonnet $3/$15 | ~$0.08 |
| 12 × Sphere Agents | ~50K | ~50K | Opus $5/$25 | ~$1.50 |
| 1 × Meta Agent | ~20K | ~5K | Opus $5/$25 | ~$0.23 |
| 1 × Compressor | ~20K | ~4K | Sonnet $3/$15 | ~$0.12 |
| Embeddings | — | — | OpenAI | ~$0.01 |
| **ИТОГО (1 учение)** | | | | **~$2.05** |

**Полная система (8 учений):**

| Компонент | Input tokens | Output tokens | Модель | Стоимость |
|-----------|-------------|---------------|--------|-----------|
| 8 × Интерпретация | ~82K | ~32K | Sonnet $3/$15 | ~$0.73 |
| 1 × Merger | ~33K | ~18K | Sonnet $3/$15 | ~$0.37 |
| 12 × Sphere Agents | ~72K | ~60K | Opus $5/$25 | ~$1.86 |
| 1 × Meta Agent | ~25K | ~6K | Opus $5/$25 | ~$0.28 |
| 1 × Compressor | ~30K | ~5K | Sonnet $3/$15 | ~$0.17 |
| Embeddings | — | — | OpenAI | ~$0.02 |
| **ИТОГО (8 учений)** | | | | **~$3.43** |

### 14.2 Оптимизации

| Оптимизация | Экономия | Условие |
|-------------|----------|---------|
| Prompt Caching | -90% input | System prompts одинаковые для всех пользователей |
| Batch API | -50% всего | Время генерации 5-15 мин вместо 1 мин |
| Кэш + Batch | -70% | Комбинация |

| Масштаб | Цена/портрет (без оптимизации) | Цена/портрет (с оптимизацией) |
|---------|-------------------------------|-------------------------------|
| 1 портрет | ~$3.43 | ~$3.43 |
| 100 портретов | ~$3.43 | ~$1.50 |
| 1000 портретов | ~$3.43 | ~$1.00 |
| 10000 портретов | ~$3.43 | ~$0.80 |

---

## 15. ЗАДАЧА ДЛЯ АГЕНТА-РАЗРАБОТЧИКА

### ЗАДАЧА: Реализация системы Digital Soul Blueprint

---

### КОНТЕКСТ

Ты — backend-разработчик. Твоя задача — реализовать систему генерации цифрового портрета личности Digital Soul Blueprint.

**КЛЮЧЕВОЕ ПРАВИЛО: Архитектура строится под ВСЕ 8 учений, но на старте активно ТОЛЬКО ОДНО — Западная астрология.**

Это значит:
- Все интерфейсы, базовые классы, схемы БД, форматы — **универсальные**
- Конфиг `ACTIVE_SYSTEMS` определяет какие учения запускаются
- Подключение нового учения = 1 калькулятор + 1 агент, без изменения ядра
- На старте: `ACTIVE_SYSTEMS = ["western_astrology"]`

---

### ФАЗА 1 — MVP: Полный цикл с одним учением (Приоритет: КРИТИЧЕСКИЙ)

#### Задача 1.0: Конфигурация и базовые классы

**Создать универсальную инфраструктуру:**

```python
# config.py
ACTIVE_SYSTEMS: list[str] = ["western_astrology"]
# Когда подключаем новые учения — просто добавляем в список:
# ACTIVE_SYSTEMS = ["western_astrology", "matrix_of_destiny", "bazi"]

SYSTEM_REGISTRY: dict = {
    "western_astrology": {
        "calculator": "calculators.western_astrology.WesternAstrologyCalculator",
        "agent": "interpreters.western_astrology_agent.WesternAstrologyAgent",
        "rag_collection": "books_western_astrology",
        "active": True,
    },
    "matrix_of_destiny": {
        "calculator": "calculators.matrix_of_destiny.MatrixCalculator",
        "agent": "interpreters.matrix_agent.MatrixAgent",
        "rag_collection": "books_matrix",
        "active": False,  # Будет True в Фазе 2
    },
    # ... остальные 6 учений — структура готова, active: False
}
```

**Базовые классы:**

```python
# calculators/base.py
class Calculator(ABC):
    system_name: str
    
    @abstractmethod
    async def calculate(self, birth_data: BirthData) -> dict:
        """Возвращает JSON с сырыми расчётами."""
        pass

# interpreters/base.py
class InterpretationAgent(ABC):
    system_name: str
    model: str = "claude-sonnet-4-6"
    
    @abstractmethod
    async def interpret(self, raw_data: dict) -> list[UniversalInsightSchema]:
        """Интерпретирует сырые данные в UIS."""
        pass

# interpreters/schemas.py
class UniversalInsightSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_system: str
    position: str
    spheres_affected: list[int]
    primary_sphere: int
    influence_level: Literal["high", "medium", "low"]
    polarity: Literal["light", "shadow", "dual"]
    light_aspect: str
    shadow_aspect: str
    energy_description: str
    core_theme: str
    developmental_task: str
    integration_key: str
    triggers: list[str]
    timing: Optional[str] = None
    book_references: list[str] = []
    confidence: float = 0.5
    weight: float = 0.5
```

**Pipeline с динамическим количеством учений:**

```python
# pipeline/orchestrator.py
class PortraitOrchestrator:
    def __init__(self):
        self.active_systems = self._load_active_systems()
    
    def _load_active_systems(self):
        """Загружает только активные калькуляторы и агентов из SYSTEM_REGISTRY."""
        systems = []
        for name, config in SYSTEM_REGISTRY.items():
            if config["active"]:
                systems.append({
                    "name": name,
                    "calculator": import_class(config["calculator"])(),
                    "agent": import_class(config["agent"])(),
                })
        return systems
    
    async def generate(self, birth_data: BirthData) -> str:
        # Автоматически масштабируется от 1 до 8 учений
        raw_results = await asyncio.gather(*[
            s["calculator"].calculate(birth_data) 
            for s in self.active_systems
        ])
        interpretations = await asyncio.gather(*[
            s["agent"].interpret(raw) 
            for s, raw in zip(self.active_systems, raw_results)
        ])
        # ... далее Merger → Sphere Agents → Meta → Compressor → Save
```

---

#### Задача 1.1: Калькулятор западной астрологии (Слой 1)

**Единственный активный калькулятор на старте.**

- Использовать библиотеку `pyswisseph`
- Вход: дата, время, место (координаты)
- Выход: JSON по формату из секции 3.2

**Что рассчитывать:**
- Все планеты: Солнце, Луна, Меркурий, Венера, Марс, Юпитер, Сатурн, Уран, Нептун, Плутон
- Дополнительные точки: Лилит (Mean Black Moon), Северный/Южный Узлы, Колесо Фортуны
- Для каждой планеты: знак, дом, градус, скорость, ретроградность, стационарность, достоинство (domicile/exaltation/detriment/fall/neutral)
- Аспекты между всеми парами: конъюнкция (0°), секстиль (60°), квадрат (90°), трин (120°), оппозиция (180°)
- Орбы: Солнце/Луна 10°, личные планеты 8°, социальные 6°, высшие 5°
- Для аспектов: орб, тип, сходящийся/расходящийся, точный (орб < 1°), диссоциированный
- Дома: система Плацидус, куспиды всех 12 домов
- Стеллиумы: 3+ планет в знаке или доме
- Полусферы: Север/Юг, Восток/Запад, квадранты
- ASC, MC, управители домов

**Тесты:** минимум 5 известных дат → сверить с astro.com

---

#### Задача 1.2: Агент интерпретации — WesternAstrologyAgent (Слой 2)

**Единственный активный агент на старте.**

Реализовать `WesternAstrologyAgent(InterpretationAgent)`:
- Получает JSON натальной карты
- Генерирует 40-80 UIS-объектов (каждая планета, аспект, стеллиум → отдельный UIS)
- Привязывает каждый UIS к сферам 1-12
- Проставляет influence_level (high/medium/low) по критериям из секции 10.1

**System prompt для агента:**
```
Ты — профессиональный астролог-интерпретатор. 
Получаешь сырые данные натальной карты.

ЗАДАЧА: Для КАЖДОГО значимого элемента карты создай 
отдельный объект Universal Insight Schema.

ОБЯЗАТЕЛЬНО интерпретировать:
- Каждую планету в знаке и доме (10+ объектов)
- Каждый аспект с орбом < 8° (15-25 объектов)
- Каждый стеллиум (1-3 объекта)
- ASC и его управителя (2 объекта)
- MC и его управителя (2 объекта)
- Узлы (2 объекта)
- Полусферы и квадранты (1-2 объекта)

Для КАЖДОГО объекта:
- Привяжи к primary_sphere (1-12)
- Укажи influence_level: high/medium/low
- Напиши light_aspect (3+ предложений)
- Напиши shadow_aspect (3+ предложений)
- Укажи конкретные triggers
- Используй язык ощущений, не абстракций

ИТОГО: 40-80 объектов на карту. Ничего не пропускай.
```

**RAG на старте:** Встроить ключевые интерпретации из книг прямо в system prompt (hardcoded). Полноценный RAG с Qdrant — Фаза 2.

---

#### Задача 1.3: Synthesis Oracle (Слой 3) — работает одинаково для 1 и 8 учений

**4 компонента:**

1. **Merger** (Sonnet 4.6):
   - Вход: массив UIS от ВСЕХ активных агентов (на старте — от одного)
   - Группирует по `primary_sphere`
   - Выход: `{sphere_1: [UIS...], sphere_2: [UIS...], ...}`

2. **SphereAgent × 12** (Opus 4.6, параллельно):
   - Каждый получает UIS для одной сферы
   - System prompt из секции 5.1.2 с адаптацией:
     ```
     # При 1 активном учении промпт адаптируется:
     if len(active_systems) == 1:
         prompt += """
         Сейчас активно 1 учение. 
         Слой 2 (цепочки): ищи ВНУТРИСИСТЕМНЫЕ связи — 
         как разные элементы одного учения подтверждают 
         или противоречат друг другу.
         Convergence_score = степень внутренней согласованности.
         """
     else:
         prompt += """
         Активно {n} учений.
         Слой 2 (цепочки): ищи МЕЖСИСТЕМНЫЕ связи —
         где разные учения указывают на одно и то же.
         """
     ```
   - Выход: 5-слойная структура

3. **MetaAgent** (Opus 4.6):
   - Межсферные суперпаттерны
   
4. **Compressor** (Sonnet 4.6):
   - Краткий формат: 1 абзац на сферу

---

#### Задача 1.4: Хранение (Слой 4)

1. Создать ВСЕ таблицы из секции 6.1 в Supabase (полная схема, не только для астрологии)
2. Поле `source_system` в `portrait_facts` — ключ для фильтрации по учениям
3. Таблица `digital_portraits` получает поле:
   ```sql
   systems_used TEXT[] DEFAULT '{}' -- ["western_astrology"] на старте
   ```
4. Реализовать сохранение + embeddings
5. Реализовать semantic search
6. **Перегенерация:** при подключении нового учения → существующий портрет дополняется новыми фактами и пересинтезируется (Слой 3 перезапускается с расширенным набором UIS)

---

#### Задача 1.5: API endpoints

```python
# Полный набор — работает сразу, масштабируется автоматически

# POST /api/portraits/generate
# Body: { "date": "1988-07-02", "time": "00:40", "place": "Ternopil, Ukraine" }
# Response: { "portrait_id": "uuid", "status": "generating", "systems": ["western_astrology"] }

# GET /api/portraits/{portrait_id}
# Response: полный портрет (детальный + краткий)

# GET /api/portraits/{portrait_id}/sphere/{sphere_num}
# Response: одна сфера (5 слоёв)

# GET /api/portraits/{portrait_id}/sphere/{sphere_num}?format=brief
# Response: краткий формат одной сферы

# GET /api/portraits/{portrait_id}/brief
# Response: краткий формат (12 абзацев + overall)

# POST /api/portraits/{portrait_id}/search
# Body: { "query": "почему мне сложно с деньгами" }
# Response: релевантные чанки портрета

# GET /api/portraits/{portrait_id}/status
# Response: { "status": "generating|ready|error", "progress": 0.75, "systems_used": [...] }

# GET /api/systems
# Response: { "active": ["western_astrology"], "planned": ["matrix_of_destiny", ...] }

# POST /api/portraits/{portrait_id}/regenerate
# Перегенерация портрета (например, после подключения нового учения)
```

---

#### Задача 1.6: Минимальный UI

1. **Страница ввода:** дата, время, место рождения. Показывает какие учения активны
2. **Страница ожидания:** прогресс-бар генерации
3. **Страница портрета:**
   - Переключатель: **ДЕТАЛЬНЫЙ** / **КРАТКИЙ** формат
   - 12 вкладок по сферам
   - В детальном: 5 слоёв, раскрывающиеся блоки
   - Метки влияния (🔴🟡🟢) у каждого элемента
   - Convergence badges у цепочек и паттернов
   - Source stack — из какого учения (на старте всё "western_astrology", при расширении — показывает все)
   - Баннер: "Портрет построен на основе 1 из 8 учений. Подключайте больше для глубины."

---

### ФАЗА 2 — Простые учения (ПОСЛЕ завершения Фазы 1)

#### Задача 2.1: Калькуляторы + агенты
- Матрица Судьбы: калькулятор (алгоритм в секции 15, задача 1.1 старого документа) + агент
- Ба Цзы: калькулятор (таблицы Ган Чжи) + агент
- Цолькин: калькулятор (260 кинов) + агент
- Нумерология: калькулятор (Пифагор) + агент

#### Задача 2.2: Активация
- Добавить в `ACTIVE_SYSTEMS`
- Конвергенция включается автоматически
- Перегенерация существующих портретов (опционально, по запросу пользователя)

#### Задача 2.3: RAG-базы книг
- Настроить Qdrant
- Загрузить книги из секции 11.2
- Подключить к агентам Слоя 2

---

### ФАЗА 3 — Сложные учения + оптимизация (ПОСЛЕ завершения Фазы 2)

#### Задача 3.1: Human Design + Gene Keys + Ведическая астрология
#### Задача 3.2: Prompt Caching + Batch API
#### Задача 3.3: Агент-помощник (чат по портрету)

---

### КРИТЕРИИ ПРИЁМКИ

#### Фаза 1 (MVP — 1 учение):
- [ ] Базовые классы Calculator и InterpretationAgent универсальны для любого учения
- [ ] ACTIVE_SYSTEMS конфиг работает: при добавлении учения пайплайн автоматически расширяется
- [ ] Калькулятор западной астрологии: тесты на 5+ картах пройдены
- [ ] WesternAstrologyAgent: генерирует 40-80 UIS на карту
- [ ] Sphere Agents: 5-слойный портрет по 12 сферам
- [ ] Детальный и краткий форматы работают
- [ ] Метки влияния (🔴🟡🟢) на всех элементах
- [ ] Портрет сохраняется в Supabase с embeddings
- [ ] Semantic search по портрету работает
- [ ] Все API endpoints работают
- [ ] UI показывает оба формата
- [ ] Время генерации < 90 секунд
- [ ] Стоимость < $2.50 за портрет
- [ ] Схема БД готова под все 8 учений (хотя активно 1)

#### Фаза 2 (5 учений):
- [ ] 5 калькуляторов + 5 агентов работают
- [ ] Межсистемная конвергенция показывает реальные совпадения
- [ ] RAG подключён

#### Фаза 3 (8 учений + оптимизация):
- [ ] Все 8 учений активны
- [ ] Стоимость < $1.50 за портрет (с оптимизацией)
- [ ] Агент-помощник отвечает на вопросы по портрету

---

### СТРУКТУРА ПРОЕКТА

```
digital-soul-blueprint/
├── README.md
├── docker-compose.yml
├── .env.example
│
├── calculators/                    # Слой 1
│   ├── __init__.py
│   ├── base.py                     # Базовый класс Calculator
│   ├── western_astrology.py
│   ├── vedic_astrology.py
│   ├── human_design.py
│   ├── gene_keys.py
│   ├── numerology.py
│   ├── matrix_of_destiny.py
│   ├── bazi.py
│   ├── tzolkin.py
│   └── tests/
│       ├── test_western_astrology.py
│       ├── test_bazi.py
│       └── ...
│
├── interpreters/                   # Слой 2
│   ├── __init__.py
│   ├── base.py                     # Базовый InterpretationAgent
│   ├── schemas.py                  # UniversalInsightSchema (Pydantic)
│   ├── western_astrology_agent.py
│   ├── bazi_agent.py
│   ├── matrix_agent.py
│   ├── ...
│   └── prompts/
│       ├── western_astrology.txt
│       ├── bazi.txt
│       └── ...
│
├── synthesis/                      # Слой 3
│   ├── __init__.py
│   ├── merger.py
│   ├── sphere_agent.py
│   ├── meta_agent.py
│   ├── compressor.py
│   └── prompts/
│       ├── sphere_agent.txt
│       ├── meta_agent.txt
│       └── compressor.txt
│
├── storage/                        # Слой 4
│   ├── __init__.py
│   ├── models.py                   # SQLAlchemy / Supabase models
│   ├── repository.py               # CRUD операции
│   ├── embeddings.py               # Генерация embeddings
│   ├── search.py                   # Semantic search
│   └── migrations/
│       └── 001_create_tables.sql
│
├── api/                            # FastAPI
│   ├── __init__.py
│   ├── main.py
│   ├── routes/
│   │   ├── portraits.py
│   │   └── search.py
│   └── dependencies.py
│
├── pipeline/                       # Оркестрация
│   ├── __init__.py
│   ├── orchestrator.py             # Главный пайплайн
│   └── worker.py                   # Celery worker
│
├── rag/                            # RAG для книг (Фаза 2)
│   ├── __init__.py
│   ├── loader.py
│   ├── chunker.py
│   └── retriever.py
│
└── frontend/                       # Next.js (Фаза 1 — минимальный)
    ├── app/
    │   ├── page.tsx                 # Ввод данных
    │   ├── portrait/[id]/page.tsx   # Просмотр портрета
    │   └── ...
    └── components/
        ├── SphereCard.tsx
        ├── InfluenceBadge.tsx
        ├── ConvergenceBar.tsx
        └── ...
```

---

*Документ подготовлен для передачи агенту-разработчику. Версия 1.1 FINAL.*
*Архитектура спроектирована под 8 учений. Старт с 1 учения (Западная астрология).*
*Подключение каждого нового учения = 1 калькулятор + 1 агент. Ядро не меняется.*
*Все расчёты, форматы и структуры протестированы на реальных данных (02.07.1988 00:40 Тернополь).*
*Дата: 21 марта 2026*
