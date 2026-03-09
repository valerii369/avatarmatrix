# QUANTUM SHIFT — Система визуализации сфер

## Концепция

Каждая сфера содержит 22 карты (архетипы). Каждая карта = 1 энергетическая нить в потоке к сфере. Визуальная мощность сферы определяется двумя параметрами: **сколько карт активировано** (количество нитей) и **на каком уровне каждая карта** (толщина и яркость каждой нити).

---

## Архитектура данных

### Карта (Card)

```typescript
interface Card {
  id: number;             // 0–21
  sphere_id: number;      // 0–7
  archetype: string;      // "The Magician", "The Fool", ...
  is_active: boolean;     // активирована ли карта
  hawkins_score: number;  // 0–1000 (текущий уровень осознанности)
  rank: number;           // 1–10 (computed from hawkins_score)
}
```

### Сфера (Sphere)

```typescript
interface SphereState {
  sphere_id: number;
  cards: Card[];                // 22 карты
  active_count: number;         // сколько карт активировано (0–22)
  sphere_score: number;         // агрегированный score (0.0–1.0)
  sphere_hawkins: number;       // средневзвешенный hawkins (0–1000)
  sphere_rank: number;          // итоговый LVL сферы (1–10)
}
```

---

## Формулы расчёта

### 1. Score сферы (0.0 – 1.0)

```python
sphere_score = sum(card.hawkins_score for card in active_cards) / (22 * 1000)
```

Это ключевая формула. Она гарантирует правильное масштабирование:

| Сценарий | Расчёт | sphere_score | Восприятие |
|----------|--------|-------------|------------|
| 1 карта, LVL 1 (score 20) | 20 / 22000 | 0.001 | Едва заметно |
| 5 карт, средний score 200 | 1000 / 22000 | 0.045 | Слабый поток |
| 10 карт, средний score 500 | 5000 / 22000 | 0.227 | Заметный поток |
| 10 карт, ВСЕ на максимуме | 10000 / 22000 | 0.454 | Мощный, но ~половина |
| 15 карт, средний score 700 | 10500 / 22000 | 0.477 | Чуть больше половины |
| 22 карты, средний score 500 | 11000 / 22000 | 0.500 | Ровно половина |
| 22 карты, средний score 800 | 17600 / 22000 | 0.800 | Очень мощный |
| 22 карты, ВСЕ на максимуме | 22000 / 22000 | 1.000 | АБСОЛЮТНЫЙ МАКСИМУМ |

> **10 карт на максимуме = 45%.** Визуально мощно, но явно "есть куда расти". Проблема решена.

### 2. Hawkins сферы (для отображения числа)

```python
if active_count > 0:
    sphere_hawkins = sum(card.hawkins_score for card in active_cards) / active_count
else:
    sphere_hawkins = 0
```

Это **средний hawkins активных карт** — показывает "качество" прокачки.

### 3. Rank сферы (LVL 1–10)

Rank считается от sphere_hawkins (средний уровень активных карт):

```python
def hawkins_to_rank(hawkins_peak: int) -> int:
    thresholds = [20, 50, 100, 175, 200, 310, 400, 500, 600, 1000]
    for i, t in enumerate(thresholds):
        if hawkins_peak <= t:
            return i + 1
    return 10
```

---

## Визуализация: 22 нити

### Принцип

Поток между центром и сферой состоит из **отдельных нитей**, каждая соответствует одной карте. Неактивные карты — нитей нет. Активированная карта — появляется новая нить. Уровень карты определяет свойства нити.

### Свойства каждой нити

```
card_intensity = card.hawkins_score / 1000    // 0.0 – 1.0
card_rank = hawkins_to_rank(card.hawkins_score)  // 1 – 10
```

| Свойство | LVL 1 (0–20) | LVL 5 (176–200) | LVL 10 (601–1000) |
|----------|-------------|-----------------|-------------------|
| Толщина | 0.3 px | 1.2 px | 3.0 px |
| Прозрачность | 0.04 | 0.10 | 0.22 |
| Свечение (blur) | 0 | 4 px | 14 px |
| Цвет | Тусклый, серо-цветной | Цвет сферы | Яркий + белое ядро |
| Амплитуда волны | 3 px | 12 px | 28 px |
| Скорость волны | Медленная | Средняя | Быстрая |

### Формулы нити

```javascript
// Для каждой активной карты:
const ci = card.hawkins_score / 1000;

const threadWidth    = 0.3 + ci * 2.7;        // 0.3 – 3.0 px
const threadAlpha    = 0.04 + ci * 0.18;       // 0.04 – 0.22
const threadGlow     = ci > 0.2 ? (ci - 0.2) * 17.5 : 0;  // 0 – 14 px
const threadAmplitude = 3 + ci * 25;           // 3 – 28 px
const threadSpeed    = 0.001 + ci * 0.002;     // скорость анимации
```

### Распределение нитей в потоке

22 нити распределяются **равномерно** по ширине потока. Чем больше нитей, тем шире поток визуально:

```javascript
const maxSpread = 6 + sphere_score * 50;  // ширина "русла": 6 – 56 px
const activeCards = cards.filter(c => c.is_active).sort((a, b) => a.id - b.id);

activeCards.forEach((card, index) => {
  const position = activeCards.length === 1 
    ? 0  // одна нить — по центру
    : (index / (activeCards.length - 1) - 0.5) * maxSpread;
  
  // position — смещение нити от центральной оси потока
  drawThread(ctx, x1, y1, x2, y2, position, card);
});
```

---

## Визуализация: размер сферы

Размер сферы привязан к **sphere_score** (агрегат), не к среднему:

```javascript
const visual = Math.pow(sphere_score, 1.3);  // экспоненциальная кривая

const minRadius = screenMin * 0.022;
const maxRadius = screenMin * 0.08;
const radius = minRadius + (maxRadius - minRadius) * visual;
```

| Сценарий | sphere_score | visual | Радиус |
|----------|-------------|--------|--------|
| 1 карта, LVL 1 | 0.001 | 0.000 | 2.2% (точка) |
| 5 карт, LVL 5 | 0.045 | 0.019 | 2.3% |
| 10 карт, LVL 7 | 0.182 | 0.110 | 2.9% |
| 10 карт, MAX | 0.454 | 0.347 | 4.2% |
| 22 карты, LVL 7 | 0.400 | 0.295 | 3.9% |
| 22 карты, MAX | 1.000 | 1.000 | 8.0% |

---

## Визуализация: свечение сферы (glow)

```javascript
const glowLayers = 2 + Math.floor(visual * 6);     // 2 – 8 слоёв
const glowSpread = radius + layer * (6 + visual * 18);
```

---

## Бонусные эффекты

Привязаны к **sphere_score**, появляются постепенно:

| Эффект | Порог sphere_score | Примерный сценарий |
|--------|-------------------|-------------------|
| Нити начинают "дышать" | 0.05 | 3 карты на LVL 4 |
| Появляется свечение у нитей (shadowBlur) | 0.10 | 5 карт на LVL 5 |
| Core line (яркая центральная ось потока) | 0.20 | 10 карт на LVL 5 |
| 2-е орбитальное кольцо у сферы | 0.30 | 10 карт на LVL 7 |
| Летящие частицы вдоль потока | 0.35 | 12 карт на LVL 7 |
| Inner pulse в сфере | 0.45 | 10 карт на MAX |
| Лучевой эффект от сферы | 0.60 | 15 карт на LVL 9 |
| Второе кольцо Цветка Жизни (центр) | 0.70 | 18 карт на LVL 9 |
| Полная сакральная геометрия | 0.85 | 20 карт на LVL 9+ |

---

## Центральная структура (Цветок Жизни)

Реагирует на **средний sphere_score** по всем 8 сферам:

```javascript
const globalScore = spheres.reduce((sum, s) => sum + s.sphere_score, 0) / 8;
const globalVisual = Math.pow(globalScore, 1.3);
```

---

## Supabase: структура данных

```sql
-- Карты пользователя
CREATE TABLE user_cards (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  sphere_id INT NOT NULL CHECK (sphere_id BETWEEN 0 AND 7),
  card_id INT NOT NULL CHECK (card_id BETWEEN 0 AND 21),
  is_active BOOLEAN DEFAULT false,
  hawkins_score INT NOT NULL DEFAULT 0 CHECK (hawkins_score BETWEEN 0 AND 1000),
  rank INT GENERATED ALWAYS AS (
    CASE
      WHEN hawkins_score <= 20 THEN 1
      WHEN hawkins_score <= 50 THEN 2
      WHEN hawkins_score <= 100 THEN 3
      WHEN hawkins_score <= 175 THEN 4
      WHEN hawkins_score <= 200 THEN 5
      WHEN hawkins_score <= 310 THEN 6
      WHEN hawkins_score <= 400 THEN 7
      WHEN hawkins_score <= 500 THEN 8
      WHEN hawkins_score <= 600 THEN 9
      ELSE 10
    END
  ) STORED,
  activated_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (user_id, sphere_id, card_id)
);

-- Представление: агрегат по сферам
CREATE VIEW user_sphere_stats AS
SELECT
  user_id,
  sphere_id,
  COUNT(*) FILTER (WHERE is_active) AS active_count,
  COALESCE(AVG(hawkins_score) FILTER (WHERE is_active), 0)::INT AS avg_hawkins,
  COALESCE(SUM(hawkins_score) FILTER (WHERE is_active), 0)::FLOAT 
    / (22 * 1000) AS sphere_score
FROM user_cards
GROUP BY user_id, sphere_id;

-- RLS
ALTER TABLE user_cards ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own cards" ON user_cards
  FOR ALL USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX idx_user_cards_user_sphere ON user_cards(user_id, sphere_id);
CREATE INDEX idx_user_cards_active ON user_cards(user_id, is_active) WHERE is_active;
```

---

## TypeScript: клиентская логика

```typescript
function hawkinsToRank(score: number): number {
  const t = [20, 50, 100, 175, 200, 310, 400, 500, 600, 1000];
  return (t.findIndex(v => score <= v) + 1) || 10;
}

function calcSphereState(cards: Card[]): SphereState {
  const active = cards.filter(c => c.is_active);
  const totalHawkins = active.reduce((s, c) => s + c.hawkins_score, 0);
  
  return {
    active_count: active.length,
    sphere_score: totalHawkins / (22 * 1000),          // 0.0 – 1.0
    sphere_hawkins: active.length > 0 
      ? Math.round(totalHawkins / active.length) : 0,  // средний
    sphere_rank: hawkinsToRank(
      active.length > 0 ? Math.round(totalHawkins / active.length) : 0
    ),
  };
}
```

---

## Стандартные 8 сфер × 22 карты

| sphere_id | Сфера | Иконка | Цвет RGB | Карты |
|-----------|-------|--------|----------|-------|
| 0 | Здоровье | ♡ | 120, 255, 180 | 22 архетипов |
| 1 | Финансы | ◈ | 255, 215, 80 | 22 архетипов |
| 2 | Отношения | ∞ | 255, 130, 180 | 22 архетипов |
| 3 | Карьера | ⬡ | 80, 180, 255 | 22 архетипов |
| 4 | Духовность | ✦ | 200, 160, 255 | 22 архетипов |
| 5 | Творчество | ◎ | 255, 160, 80 | 22 архетипов |
| 6 | Знания | ◇ | 100, 220, 255 | 22 архетипов |
| 7 | Социум | ⊛ | 180, 255, 160 | 22 архетипов |

**Итого: 8 × 22 = 176 карт на пользователя.**

---

## Путь пользователя (ощущение прогресса)

```
Старт
  └─ Активирует 1-ю карту → в потоке появляется тонкая одинокая нить
  └─ Прокачивает её до LVL 5 → нить становится толще, ярче
  └─ Активирует 2-ю карту → вторая тонкая нить рядом
  └─ К 5 картам → поток уже "живой", 5 волнистых нитей
  └─ Прокачивает до LVL 7 → нити плотные, появляется свечение
  └─ К 10 картам → поток широкий, сфера выросла
  └─ Все 10 на MAX → мощный поток, НО сфера ~45% (видно что есть куда расти)
  └─ 15 карт, LVL 8+ → поток как река, сфера 55%+, бонусные эффекты
  └─ 22 карты, все MAX → ПОЛНЫЙ МАКСИМУМ: 22 ярких толстых нити,
     огромная сфера, все бонусные эффекты, полная сакральная геометрия
```

**На каждом шаге есть визуальное изменение** — либо новая нить, либо утолщение существующей, либо новый бонусный эффект. Никогда не будет ощущения "застоя".

---

## Чеклист реализации

- [ ] Supabase: создать таблицу `user_cards` + view `user_sphere_stats`
- [ ] Клиент: `calcSphereState()` — агрегация карт в параметры сферы
- [ ] Визуализация: рефакторинг `drawEnergyFlow` — рисовать по 1 нити на карту
- [ ] Каждая нить: толщина, alpha, glow, amplitude привязаны к `card.hawkins_score`
- [ ] Размер сферы: привязать к `sphere_score` вместо одного `level`
- [ ] Бонусные эффекты: привязать пороги к `sphere_score`
- [ ] UI: показывать `active_count / 22` + `sphere_rank` + `sphere_hawkins`
- [ ] Анимация: плавное появление новой нити при активации карты (fade in)
- [ ] Анимация: плавное утолщение нити при росте hawkins_score (lerp)
- [ ] Тестировать сценарии: 1 карта LVL 1, 10 карт MAX, 22 карты MAX
