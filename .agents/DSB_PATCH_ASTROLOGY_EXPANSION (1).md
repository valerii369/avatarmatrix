# ПАТЧ: Расширение астрологического модуля DSB
## Добавить в существующую систему — НЕ переписывать

> Этот файл — дополнение к уже интегрированной архитектуре.
> Не трогай существующий код — только ДОБАВЛЯЙ новые элементы.

---

## ОБЩИЙ ПРИНЦИП

Все изменения затрагивают 3 файла:
1. **Калькулятор** (`calculators/western_astrology.py`) — добавить новые расчёты в выходной JSON
2. **Агент интерпретации** (`interpreters/western_astrology_agent.py`) — обновить промпт чтобы интерпретировал новые данные
3. **Тесты** (`tests/test_portrait_quality.py`) — добавить проверки на новые элементы

Выходной JSON калькулятора расширяется новыми полями. Существующие поля (`planets`, `aspects`, `cusps`, `stelliums` и т.д.) **не меняются**.

---

## БЛОК 1: КРИТИЧНЫЕ ДОПОЛНЕНИЯ (обязательно)

---

### 1.1 Хирон (Chiron)

**Что:** Астероид-планетоид, показывающий главную рану и через неё — дар целительства. Для психологического портрета — один из важнейших элементов.

**Калькулятор — добавить в массив `planets`:**

```python
# В функции расчёта планет добавить Хирон
# swisseph: SE_CHIRON = 15
chiron_data = swe.calc_ut(jd, swe.CHIRON)

# Добавить в planets[] объект:
{
    "name": "Хирон",
    "name_en": "Chiron",
    "sign": "...",
    "sign_ru": "...",
    "house": N,
    "degree": X.XXX,
    "speed": X.XXX,
    "retrograde": True/False,
    "dignity": "neutral",  # Хирон не имеет классических достоинств
    "priority": "high",     # ← Высокий приоритет для портрета
    "is_stationary": True/False
}
```

**Хирон также участвует в аспектах** — добавить его в цикл расчёта аспектов с другими планетами. Орб: 5° (как для высших планет).

**Агент — добавить в промпт:**
```
Хирон — "раненый целитель". Показывает:
- Где главная боль/рана человека (знак + дом)
- Через что происходит исцеление
- Какой целительский дар открывается через проработку

Хирон в знаке = ХАРАКТЕР раны
Хирон в доме = СФЕРА ЖИЗНИ где рана проявляется
Аспекты Хирона = как рана взаимодействует с другими энергиями

influence_level для Хирона: всегда "high" в primary_sphere его дома.
```

---

### 1.2 Квинконс (150°) — шестой аспект

**Что:** Аспект дискомфорта и принудительной адаптации. Не конфликт, не гармония — "не стыкуется, но приходится жить с этим". Критичен для двух вещей:
1. Психологические паттерны дискомфорта
2. **Без квинконса невозможно найти фигуру Йод (Перст Судьбы)**

**Калькулятор — добавить в расчёт аспектов:**

```python
# В списке аспектов добавить:
ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
    "quincunx": 150,      # ← ДОБАВИТЬ
}

# Орб для квинконса: 3° (строже чем мажорные)
QUINCUNX_ORB = 3.0
```

**В выходном JSON аспекты с type="quincunx" появляются в том же массиве `aspects[]`.**

**Агент — добавить в промпт:**
```
Квинконс (150°) — аспект вынужденной адаптации:
- Две энергии НЕ совместимы по стихии и модальности
- Человек чувствует постоянный дискомфорт между этими сферами
- Нет простого решения — только принятие парадокса
- influence_level: "medium" (если орб < 2° — "high")

Квинконс = "я не могу это примирить, но должен жить с обоими".
Это НЕ конфликт (квадрат) и НЕ напряжение (оппозиция).
Это НЕСОВМЕСТИМОСТЬ, требующая зрелости.
```

---

### 1.3 Аспектные фигуры (конфигурации)

**Что:** Комбинации аспектов, образующие геометрические фигуры. Это ГЛАВНОЕ из пропущенного — отдельные аспекты как буквы, фигуры как слова.

**Калькулятор — добавить новое поле `aspect_patterns[]` в выходной JSON:**

```python
def find_aspect_patterns(planets: list, aspects: list) -> list:
    """Находит аспектные фигуры в карте."""
    patterns = []
    
    # ─── Тау-квадрат ───
    # Два квадрата + оппозиция. Вершина = фокусная планета
    # Пример: A □ B, A □ C, B ☍ C → A = вершина
    for opp in [a for a in aspects if a["type"] == "opposition"]:
        p1, p2 = opp["planet1"], opp["planet2"]
        for sq in [a for a in aspects if a["type"] == "square"]:
            if sq["planet1"] in (p1, p2) or sq["planet2"] in (p1, p2):
                apex = sq["planet1"] if sq["planet1"] not in (p1, p2) else sq["planet2"]
                # Проверить второй квадрат
                other = p1 if sq["planet1"] == apex or sq["planet2"] == apex else p2
                # ... (найти полный тау-квадрат)
                if valid_t_square:
                    patterns.append({
                        "type": "t_square",
                        "planets": [apex, p1, p2],
                        "apex": apex,  # Фокусная планета — САМАЯ ВАЖНАЯ
                        "apex_sign": "...",
                        "apex_house": N,
                        "missing_leg_sign": "...",  # Пустой знак напротив вершины
                        "missing_leg_house": N,
                    })
    
    # ─── Большой трин ───
    # Три трина между тремя планетами
    # Пример: A △ B, B △ C, A △ C
    # ... (найти все треугольники из тринов)
    # if valid_grand_trine:
    #     patterns.append({
    #         "type": "grand_trine",
    #         "planets": [A, B, C],
    #         "element": "Earth/Fire/Air/Water",  # Все три в одной стихии
    #     })
    
    # ─── Йод (Перст Судьбы) ───
    # Два квинконса + секстиль. Вершина = "Божий палец"
    # Пример: A ⚹ B, A ⟠ C, B ⟠ C → C = вершина (apex)
    for sxt in [a for a in aspects if a["type"] == "sextile"]:
        p1, p2 = sxt["planet1"], sxt["planet2"]
        for qnx in [a for a in aspects if a["type"] == "quincunx"]:
            if qnx["planet1"] in (p1, p2) or qnx["planet2"] in (p1, p2):
                apex = qnx["planet1"] if qnx["planet1"] not in (p1, p2) else qnx["planet2"]
                # Проверить второй квинконс от apex ко второй планете секстиля
                # ... 
                # if valid_yod:
                #     patterns.append({
                #         "type": "yod",
                #         "planets": [apex, p1, p2],
                #         "apex": apex,
                #         "apex_sign": "...",
                #         "apex_house": N,
                #     })
    
    # ─── Большой крест ───
    # 4 квадрата + 2 оппозиции. Все 4 планеты в одной модальности.
    # ... (найти если есть)
    # patterns.append({"type": "grand_cross", "planets": [...], "modality": "Cardinal/Fixed/Mutable"})
    
    # ─── Кайт ───
    # Большой трин + оппозиция от одной из его планет
    # ... (найти если есть)
    # patterns.append({"type": "kite", "planets": [...], "apex": "..."})
    
    # ─── Мистический прямоугольник ───
    # 2 оппозиции + 2 трина + 2 секстиля
    # ... (найти если есть)
    
    return patterns
```

**Выходной JSON — новое поле:**
```json
{
  "planets": [...],
  "aspects": [...],
  "aspect_patterns": [
    {
      "type": "t_square",
      "planets": ["Moon", "Mars", "Jupiter"],
      "apex": "Moon",
      "apex_sign": "Virgo",
      "apex_house": 6,
      "missing_leg_sign": "Pisces",
      "missing_leg_house": 12
    },
    {
      "type": "grand_trine",
      "planets": ["Moon", "Saturn", "Neptune"],
      "element": "Earth"
    }
  ]
}
```

**Агент — добавить в промпт:**
```
АСПЕКТНЫЕ ФИГУРЫ — интерпретируй КАЖДУЮ найденную фигуру как ОТДЕЛЬНЫЙ UIS:

Тау-квадрат:
- influence_level: ВСЕГДА "high"
- Вершина (apex) = главная точка напряжения и фокус энергии
- Пустая нога (missing leg) = зона, которую нужно РАЗВИВАТЬ для баланса
- primary_sphere = дом вершины
- Это ГЛАВНЫЙ двигатель жизни. Все ресурсы направляются сюда.

Большой трин:
- influence_level: "high"  
- Зона врождённого таланта, "течёт само"
- element определяет характер: Огонь=творчество, Земля=практика, 
  Воздух=общение, Вода=эмоции
- ТЕНЬ: лень, всё даётся легко → не развивается

Йод (Перст Судьбы):
- influence_level: ВСЕГДА "high"
- Самая кармическая фигура. "Вселенная тычет пальцем: иди ТУДА"
- Вершина = миссия, которая ощущается как неизбежность
- Два квинконса = постоянный дискомфорт, пока не примешь миссию
- primary_sphere = дом вершины

Большой крест:
- influence_level: ВСЕГДА "high"
- Постоянное давление с 4 сторон, нет покоя
- modality = где давление: Cardinal=действие, Fixed=удержание, Mutable=адаптация

Кайт:
- influence_level: "high"
- Талант (большой трин) + направление (оппозиция) = реализованный потенциал
```

---

### 1.4 Элементный и модальный баланс

**Что:** Сколько планет в каждой стихии (Огонь/Земля/Воздух/Вода) и модальности (Кардинальный/Фиксированный/Мутабельный). Определяет **базовый темперамент**.

**Калькулятор — добавить в `technical_summary`:**

```python
def calc_element_balance(planets: list) -> dict:
    """Считает распределение по стихиям и модальностям."""
    
    ELEMENTS = {
        "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
        "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
        "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
        "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
    }
    
    MODALITIES = {
        "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal",
        "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
        "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable",
    }
    
    # Считаем только основные 10 планет (без узлов, лилит, фортуны)
    main_planets = [p for p in planets if p["name_en"] in MAIN_PLANET_NAMES]
    
    elements = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
    modalities = {"Cardinal": 0, "Fixed": 0, "Mutable": 0}
    
    for p in main_planets:
        elements[ELEMENTS[p["sign"]]] += 1
        modalities[MODALITIES[p["sign"]]] += 1
    
    # Доминанта и дефицит
    dominant_element = max(elements, key=elements.get)
    deficit_element = min(elements, key=elements.get)
    dominant_modality = max(modalities, key=modalities.get)
    
    return {
        "elements": elements,
        "modalities": modalities,
        "dominant_element": dominant_element,
        "deficit_element": deficit_element,
        "dominant_modality": dominant_modality,
    }
```

**Выходной JSON — расширить `technical_summary`:**
```json
{
  "technical_summary": {
    "quadrants": {...},
    "hemispheres": {...},
    "elements": {
      "Fire": 1,
      "Earth": 6,
      "Air": 1,
      "Water": 2
    },
    "modalities": {
      "Cardinal": 5,
      "Fixed": 2,
      "Mutable": 3
    },
    "dominant_element": "Earth",
    "deficit_element": "Air",
    "dominant_modality": "Cardinal"
  }
}
```

**Агент — добавить в промпт:**
```
ЭЛЕМЕНТНЫЙ БАЛАНС — создай 1 UIS с primary_sphere = 1 (Идентичность):

Доминанта стихии = базовый темперамент:
- Earth доминирует → практик, материалист, строитель
- Fire доминирует → лидер, вдохновитель, импульсивен
- Air доминирует → коммуникатор, мыслитель, поверхностен
- Water доминирует → эмпат, интуитив, поглощён эмоциями

Дефицит стихии = слепое пятно:
- Дефицит Fire → сложно начинать, мало энтузиазма
- Дефицит Earth → оторван от реальности, проблемы с материей
- Дефицит Air → сложно объяснить себя, мало объективности
- Дефицит Water → не чувствует эмоции (свои и чужие)

Доминанта модальности = стиль действия:
- Cardinal → инициирует, но не доводит
- Fixed → упорен, но ригиден
- Mutable → адаптивен, но нестабилен

influence_level: "high" — это определяющая характеристика темперамента.
```

---

### 1.5 Полные достоинства (detriment + fall)

**Что:** Сейчас считаем только domicile и exaltation. Добавить detriment (изгнание) и fall (падение).

**Калькулятор — расширить таблицу достоинств:**

```python
DIGNITIES = {
    # planet: {domicile: [...], exaltation: [...], detriment: [...], fall: [...]}
    "Sun":     {"domicile": ["Leo"], "exaltation": ["Aries"], "detriment": ["Aquarius"], "fall": ["Libra"]},
    "Moon":    {"domicile": ["Cancer"], "exaltation": ["Taurus"], "detriment": ["Capricorn"], "fall": ["Scorpio"]},
    "Mercury": {"domicile": ["Gemini", "Virgo"], "exaltation": ["Virgo"], "detriment": ["Sagittarius", "Pisces"], "fall": ["Pisces"]},
    "Venus":   {"domicile": ["Taurus", "Libra"], "exaltation": ["Pisces"], "detriment": ["Scorpio", "Aries"], "fall": ["Virgo"]},
    "Mars":    {"domicile": ["Aries", "Scorpio"], "exaltation": ["Capricorn"], "detriment": ["Libra", "Taurus"], "fall": ["Cancer"]},
    "Jupiter": {"domicile": ["Sagittarius", "Pisces"], "exaltation": ["Cancer"], "detriment": ["Gemini", "Virgo"], "fall": ["Capricorn"]},
    "Saturn":  {"domicile": ["Capricorn", "Aquarius"], "exaltation": ["Libra"], "detriment": ["Cancer", "Leo"], "fall": ["Aries"]},
    "Uranus":  {"domicile": ["Aquarius"], "exaltation": ["Scorpio"], "detriment": ["Leo"], "fall": ["Taurus"]},
    "Neptune": {"domicile": ["Pisces"], "exaltation": ["Leo"], "detriment": ["Virgo"], "fall": ["Aquarius"]},
    "Pluto":   {"domicile": ["Scorpio"], "exaltation": ["Aries"], "detriment": ["Taurus"], "fall": ["Libra"]},
}

# dignity_score: domicile=5, exaltation=4, neutral=0, detriment=-3, fall=-4
```

**Поле `dignity` в planets[] теперь может быть:** `"domicile"`, `"exaltation"`, `"neutral"`, `"detriment"`, `"fall"`

**Агент — добавить в промпт:**
```
ДОСТОИНСТВА влияют на influence_level:
- domicile / exaltation → планета сильная, influence повышается
- detriment → планета "не в своей тарелке", работает через дискомфорт
- fall → планета в слабейшей позиции, требует осознанной проработки

Планета в detriment/fall — НЕ "плохо". Это зона обязательного роста.
Создай отдельный UIS если планета в detriment или fall.
```

---

### 1.6 Диспозиторные цепочки

**Что:** Каждая планета "управляется" планетой-хозяином знака, где она стоит. Цепочка ведёт к **финальному диспозитору** — самой влиятельной планете карты.

**Калькулятор — заполнить поле `dispositor_chains` (сейчас пустое `{}`):**

```python
SIGN_RULERS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Pluto", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Uranus", "Pisces": "Neptune",
}

def calc_dispositor_chains(planets: list) -> dict:
    """Строит цепочку диспозиторов и находит финального."""
    
    # Для каждой планеты: кто ею управляет?
    chains = {}
    for p in planets:
        ruler = SIGN_RULERS.get(p["sign"])
        if ruler and ruler != p["name_en"]:  # Если не в обители (не управляет сама собой)
            chains[p["name_en"]] = ruler
    
    # Найти финального диспозитора
    # Финальный = планета в своём знаке (domicile), к которой ведут все цепочки
    # Или взаимная рецепция (два финальных)
    final_dispositors = [p["name_en"] for p in planets if p["dignity"] == "domicile"]
    
    # Взаимная рецепция: A в знаке B, B в знаке A
    mutual_receptions = []
    for i, p1 in enumerate(planets):
        for p2 in planets[i+1:]:
            ruler_of_p1_sign = SIGN_RULERS.get(p1["sign"])
            ruler_of_p2_sign = SIGN_RULERS.get(p2["sign"])
            if ruler_of_p1_sign == p2["name_en"] and ruler_of_p2_sign == p1["name_en"]:
                mutual_receptions.append([p1["name_en"], p2["name_en"]])
    
    return {
        "chains": chains,  # {"Sun": "Saturn", "Moon": "Mercury", ...}
        "final_dispositors": final_dispositors,  # ["Saturn", "Pluto"]
        "mutual_receptions": mutual_receptions,  # [["Venus", "Uranus"]]
    }
```

**Агент — добавить в промпт:**
```
ДИСПОЗИТОРНЫЕ ЦЕПОЧКИ:
- Финальный диспозитор = "босс" всей карты. Создай UIS с influence_level "high"
  и primary_sphere = дом финального диспозитора.
- Если 2 финальных (как Сатурн и Плутон в нашей тестовой карте) — 
  оба равноважны, создай UIS для каждого.
- Взаимная рецепция = две планеты помогают друг другу. 
  influence_level "medium", затрагивает сферы обоих домов.
```

---

## БЛОК 2: ЖЕЛАТЕЛЬНЫЕ ДОПОЛНЕНИЯ

---

### 2.1 Минорные аспекты: полуквадрат (45°) и сескиквадрат (135°)

**Что:** "Скрытое раздражение". Не мощные как мажорные, но создают фоновое напряжение.

**Калькулятор:**
```python
# Добавить в ASPECTS:
"semi_square": 45,       # Орб: 2°
"sesquiquadrate": 135,   # Орб: 2°
```

**Агент:** `influence_level: "low"`. Интерпретировать только если орб < 1.5° или если участвует в паттерне с другими минорными аспектами.

---

### 2.2 Квинтиль (72°) и биквинтиль (144°)

**Что:** Аспекты **творческого таланта и уникальности**. Показывают где человек одарён необычным образом.

**Калькулятор:**
```python
"quintile": 72,          # Орб: 2°
"biquintile": 144,       # Орб: 2°
```

**Агент:** `influence_level: "low"` (повышать до `"medium"` если задействовано Солнце, Луна или управитель ASC). Тема: "здесь ты гений по-своему, не как все".

---

### 2.3 Критические градусы (0° и 29°)

**Что:** Планета в 0° знака = "только вошла", энергия нестабильная, новичок. Планета в 29° = "анаретический градус", завершение цикла, кармический багаж, ощущение срочности.

**Калькулятор — добавить поле в planets[]:**
```python
{
    "critical_degree": None,  # или "0_degree" или "29_degree"
    "degree_in_sign": 14.95,  # градус ВНУТРИ знака (0-30)
}
```

```python
def check_critical_degree(degree_in_sign: float) -> str | None:
    if degree_in_sign < 1.0:
        return "0_degree"
    elif degree_in_sign > 29.0:
        return "29_degree"
    return None
```

**Агент:**
```
0° — "новорождённая" энергия: неуверенность, свежесть, потенциал.
29° — "анаретический градус": срочность, кармическое завершение, 
      ощущение "должен успеть". influence_level: "medium".
```

---

### 2.4 Деканаты

**Что:** Каждый знак (30°) делится на 3 деканата по 10°. Каждый деканат имеет своего суб-управителя, уточняющего характер планеты.

**Калькулятор — добавить в planets[]:**
```python
{
    "decan": 1,           # 1, 2 или 3
    "decan_ruler": "Mars", # Управитель деканата
}

def get_decan(degree_in_sign: float) -> tuple[int, str]:
    """Возвращает номер деканата и его управителя."""
    # Халдейская система деканатов
    DECAN_RULERS = {
        "Aries":   ["Mars", "Sun", "Jupiter"],
        "Taurus":  ["Venus", "Mercury", "Saturn"],
        "Gemini":  ["Mercury", "Venus", "Uranus"],
        # ... (полная таблица для всех 12 знаков)
    }
    decan = 1 if degree_in_sign < 10 else (2 if degree_in_sign < 20 else 3)
    ruler = DECAN_RULERS[sign][decan - 1]
    return decan, ruler
```

**Агент:** `influence_level: "low"`. Упоминать в описании планеты как уточняющий штрих, не как отдельный UIS (если только деканат не управляется планетой, которая сама значима в карте).

---

### 2.5 Арабские точки (помимо Фортуны)

**Что:** Расчётные чувствительные точки. Фортуна уже есть. Добавить самые важные:

**Калькулятор:**
```python
# Точка Духа (Part of Spirit) — внутренняя мотивация
spirit = asc + sun - moon  # (инверсия Фортуны)

# Точка Брака — партнёрство
marriage = asc + dsc - venus

# Точка Профессии — карьера  
profession = asc + mc - sun
```

**Добавить в JSON как отдельные объекты в `planets[]` с `priority: "additional"`.**

**Агент:** `influence_level: "low"`. Использовать как подтверждение основных факторов, не как самостоятельные UIS.

---

### 2.6 Сабианские символы

**Что:** Для каждого из 360° зодиака есть символический образ (Sabian Symbols by Marc Edmund Jones). Добавляет "поэтику" портрету.

**Калькулятор:**
```python
# Таблица 360 символов (JSON файл)
# Для каждой планеты: округлить градус вверх → найти символ
def get_sabian_symbol(degree: float) -> str:
    sabian_degree = math.ceil(degree % 30) or 30
    sign_index = int(degree / 30)
    return SABIAN_SYMBOLS[sign_index][sabian_degree]
```

**Добавить в planets[]:**
```json
{
    "sabian_symbol": "A mountain pilgrimage"
}
```

**Агент:** `influence_level: "low"`. Использовать как образную метафору в описании. НЕ создавать отдельный UIS — вплетать в описание планеты.

---

## ИТОГО: ЧТО ДОБАВЛЯЕТСЯ В КАЛЬКУЛЯТОР

### Новые поля в существующих структурах:

```
planets[] — для КАЖДОЙ планеты добавить:
  + critical_degree: "0_degree" | "29_degree" | null
  + degree_in_sign: float (0-30)
  + decan: int (1-3)
  + decan_ruler: str
  + sabian_symbol: str

// Хирон — новый объект в planets[]
```

### Новые структуры в выходном JSON:

```
aspects[] — добавить типы:
  + "quincunx" (150°, орб 3°)
  + "semi_square" (45°, орб 2°)
  + "sesquiquadrate" (135°, орб 2°)
  + "quintile" (72°, орб 2°)
  + "biquintile" (144°, орб 2°)

+ aspect_patterns[]: array  ← НОВОЕ ПОЛЕ
  Фигуры: t_square, grand_trine, yod, grand_cross, kite, 
           mystic_rectangle

technical_summary — расширить:
  + elements: {Fire: N, Earth: N, Air: N, Water: N}
  + modalities: {Cardinal: N, Fixed: N, Mutable: N}
  + dominant_element: str
  + deficit_element: str
  + dominant_modality: str

dispositor_chains — ЗАПОЛНИТЬ (сейчас пустое {}):
  + chains: {planet: ruler, ...}
  + final_dispositors: [str, ...]
  + mutual_receptions: [[str, str], ...]
```

---

## ИТОГО: ЧТО ДОБАВЛЯЕТСЯ В АГЕНТ (промпт)

Добавить в system prompt агента `WesternAstrologyAgent` секции:

1. **Хирон** — отдельный UIS, influence "high"
2. **Квинконс** — отдельный UIS при орбе < 3°, influence "medium"
3. **Аспектные фигуры** — КАЖДАЯ фигура = отдельный UIS, influence "high"
4. **Элементный баланс** — 1 UIS в сфере 1, influence "high"
5. **Полные достоинства** — detriment/fall = отдельный UIS
6. **Финальный диспозитор** — UIS с influence "high"
7. **Минорные аспекты** — influence "low", только при орбе < 1.5°
8. **Критические градусы** — упоминать в описании планеты
9. **Деканаты** — уточняющий штрих в описании
10. **Сабианские символы** — образная метафора в описании

**Ожидаемое увеличение UIS:** с 40-80 до **55-100** на карту.

---

## ТЕСТЫ — добавить в `test_portrait_quality.py`

```python
def test_chiron_present():
    """Хирон рассчитан и интерпретирован."""
    raw = await calc.calculate(test_birth_data)
    chiron = [p for p in raw["planets"] if p["name_en"] == "Chiron"]
    assert len(chiron) == 1, "Хирон отсутствует в расчётах"
    
    insights = await agent.interpret(raw)
    chiron_uis = [i for i in insights if "chiron" in i.position.lower() or "хирон" in i.position.lower()]
    assert len(chiron_uis) >= 1, "Хирон не интерпретирован"

def test_quincunx_aspects():
    """Квинконсы рассчитаны."""
    raw = await calc.calculate(test_birth_data)
    quincunxes = [a for a in raw["aspects"] if a["type"] == "quincunx"]
    # Может быть 0, но тип должен поддерживаться
    # Для нашей карты проверить наличие
    assert isinstance(quincunxes, list)

def test_aspect_patterns():
    """Аспектные фигуры найдены."""
    raw = await calc.calculate(test_birth_data)
    patterns = raw.get("aspect_patterns", [])
    assert isinstance(patterns, list)
    # Для нашей карты: проверить наличие хотя бы одной фигуры
    # (Луна △ Сатурн △ Нептун может формировать большой трин в Земле)

def test_element_balance():
    """Стихийный баланс рассчитан."""
    raw = await calc.calculate(test_birth_data)
    elements = raw["technical_summary"].get("elements")
    assert elements is not None, "elements отсутствует"
    assert elements["Earth"] >= 5, f"Ожидалась доминанта Земли, получено: {elements}"
    assert raw["technical_summary"]["dominant_element"] == "Earth"

def test_dispositor_chains():
    """Диспозиторные цепочки заполнены."""
    raw = await calc.calculate(test_birth_data)
    disp = raw.get("dispositor_chains", {})
    assert disp.get("chains"), "Цепочки пустые"
    assert disp.get("final_dispositors"), "Нет финального диспозитора"
    # Сатурн и Плутон должны быть финальными (оба в обители)
    assert "Saturn" in disp["final_dispositors"]
    assert "Pluto" in disp["final_dispositors"]

def test_full_dignities():
    """Все 4 типа достоинств определяются."""
    raw = await calc.calculate(test_birth_data)
    dignities = set(p["dignity"] for p in raw["planets"])
    # Минимум domicile и neutral должны быть
    assert "domicile" in dignities
    assert "neutral" in dignities
    # detriment и fall могут быть или нет в конкретной карте

def test_critical_degrees():
    """Критические градусы определяются."""
    raw = await calc.calculate(test_birth_data)
    for p in raw["planets"]:
        assert "degree_in_sign" in p, f"{p['name_en']} без degree_in_sign"
        assert "critical_degree" in p, f"{p['name_en']} без critical_degree"
```

---

## ПОРЯДОК РЕАЛИЗАЦИИ

```
1. Хирон в planets[]                          ← 15 мин
2. Полные достоинства (detriment, fall)        ← 15 мин
3. Элементный и модальный баланс               ← 20 мин
4. Диспозиторные цепочки (заполнить пустое)    ← 30 мин
5. Квинконс (150°) в аспекты                   ← 10 мин
6. Минорные аспекты (45°, 135°, 72°, 144°)     ← 15 мин
7. Аспектные фигуры (T-квадрат, трин, Йод...)  ← 60 мин (самое сложное)
8. Критические градусы + degree_in_sign        ← 10 мин
9. Деканаты                                    ← 15 мин
10. Сабианские символы (нужна JSON-таблица)     ← 20 мин
11. Арабские точки (Spirit, Marriage, Prof)     ← 15 мин
12. Обновить промпт агента                     ← 30 мин
13. Добавить тесты                             ← 20 мин
                                        ИТОГО: ~4-5 часов
```

---

## БЛОК 3: ФРОНТЕНД — Интеграция DSB в существующий MasterHubView

### Что уже есть

```
page.tsx → activeTab === "about" → <MasterHubView userId={userId} />
MasterHubView.tsx:
  ├── subTab: "personality" | "sides" | "analysis"
  ├── "analysis" → грид 12 сфер (SPHERES_META)
  ├── клик по сфере → selectedSphere → детальный вид
  └── детальный вид → activeSphereData?.insight (ПРОСТО ТЕКСТ)
```

### Что меняем

**НЕ трогаем:** page.tsx, header, субтабы, грид сфер, стили, шрифты, CSS-переменные.

**Меняем ТОЛЬКО:** детальный вид сферы (`selectedSphere !== null`). Вместо плоского текста `insight` — структурированные блоки факторов с провалом в детали.

### Откуда берём данные

Добавить новый API-вызов в MasterHubView для получения DSB-портрета:

```tsx
// В MasterHubView.tsx — добавить рядом с существующим useSWR для hub

const { data: dsbPortrait } = useSWR(
  userId && selectedSphere ? ["dsb-sphere", userId, selectedSphere] : null,
  () => dsbAPI.getSphere(userId, sphereKeyToNumber(selectedSphere!)).then(res => res.data),
  { revalidateOnFocus: false }
);
```

```tsx
// В lib/api.ts — добавить:

export const dsbAPI = {
  getSphere: (userId: number, sphere: number) =>
    api.get(`/dsb/portraits/user/${userId}/sphere/${sphere}`),
  getPortraitBrief: (userId: number) =>
    api.get(`/dsb/portraits/user/${userId}/brief`),
};
```

```tsx
// Маппинг ключей сфер на номера
const SPHERE_KEY_TO_NUMBER: Record<string, number> = {
  IDENTITY: 1, RESOURCES: 2, COMMUNICATION: 3, ROOTS: 4,
  CREATIVITY: 5, SERVICE: 6, PARTNERSHIP: 7, TRANSFORMATION: 8,
  EXPANSION: 9, STATUS: 10, VISION: 11, SPIRIT: 12,
};

function sphereKeyToNumber(key: string): number {
  return SPHERE_KEY_TO_NUMBER[key] || 1;
}
```

---

### 3.1 Заменить Sphere Detail View в MasterHubView.tsx

Найти в MasterHubView.tsx блок:

```tsx
{/* ── Sphere Detail View ── */}
<motion.div
  key="sphere-detail"
  ...
>
  ...
  <div className="relative overflow-hidden min-h-[400px] px-2 py-4">
    ...
    <p className="text-sm leading-relaxed text-white/80 whitespace-pre-wrap font-light">
      {activeSphereData?.insight || "Глубинный смысл..."}
    </p>
  </div>
</motion.div>
```

**Заменить весь контент внутри sphere-detail на:**

```tsx
{/* ── Sphere Detail View (ОБНОВЛЁННЫЙ с DSB) ── */}
<motion.div
  key="sphere-detail"
  initial={{ opacity: 0, x: 20 }}
  animate={{ opacity: 1, x: 0 }}
  exit={{ opacity: 0, x: 20 }}
  className="space-y-5 pt-2"
>
  {/* Кнопка назад */}
  <button 
    onClick={() => { setSelectedSphere(null); setSelectedFactor(null); }}
    className="flex items-center gap-2 text-white/40 hover:text-white transition-colors text-[10px] font-bold uppercase tracking-widest pl-2"
  >
    <ArrowLeft size={16} /> Назад в Океан
  </button>

  {/* Заголовок сферы */}
  <div className="flex items-center gap-4 px-2">
    <div 
      className="w-11 h-11 rounded-2xl flex items-center justify-center shadow-lg"
      style={{ 
        backgroundColor: `${activeSphereMeta?.color}20`, 
        color: activeSphereMeta?.color,
        border: `1px solid ${activeSphereMeta?.color}30`
      }}
    >
      {activeSphereMeta && (() => {
        const Icon = ICON_MAP[activeSphereMeta.key];
        return <Icon size={22} />;
      })()}
    </div>
    <div className="flex flex-col">
      <h1 className="text-xl font-bold text-white tracking-tight mb-0.5">
        {activeSphereMeta?.name}
      </h1>
      <span className="text-[9px] font-bold text-white/30 uppercase tracking-widest leading-none">
        {activeSphereData?.status || "Стадия не определена"}
      </span>
    </div>
  </div>

  {/* Краткое описание сферы (brief) */}
  {dsbPortrait?.brief && (
    <div className="mx-2 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
      <p className="text-sm text-white/70 leading-relaxed font-light">
        {dsbPortrait.brief}
      </p>
    </div>
  )}

  {/* ═══ Карточки факторов ═══ */}
  {dsbPortrait?.factors?.length > 0 ? (
    <div className="space-y-3 px-2">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-1 h-1 rounded-full bg-white/20" />
        <span className="text-[9px] font-bold text-white/25 uppercase tracking-[0.2em]">
          Ключевые факторы ({dsbPortrait.factors.length})
        </span>
      </div>

      {dsbPortrait.factors
        .sort((a: any, b: any) => INFLUENCE_SORT[a.influence_level] - INFLUENCE_SORT[b.influence_level])
        .map((factor: any) => (
          <DSBFactorCard
            key={factor.id}
            factor={factor}
            sphereColor={activeSphereMeta?.color || "#A855F7"}
            onOpen={() => setSelectedFactor(factor)}
          />
        ))}
    </div>
  ) : (
    /* Фоллбэк на старый insight если DSB нет */
    <div className="px-2 py-4">
      <p className="text-sm leading-relaxed text-white/80 whitespace-pre-wrap font-light">
        {activeSphereData?.insight || "Глубинный смысл этой сферы раскроется в процессе твоей эволюции."}
      </p>
    </div>
  )}

  {/* ═══ Паттерны ═══ */}
  {dsbPortrait?.patterns?.length > 0 && (
    <div className="px-2 space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles size={10} className="text-white/20" />
        <span className="text-[9px] font-bold text-white/25 uppercase tracking-[0.2em]">
          Паттерны
        </span>
      </div>
      {dsbPortrait.patterns.map((p: any) => (
        <DSBPatternBlock key={p.id} pattern={p} />
      ))}
    </div>
  )}

  {/* ═══ Рекомендации ═══ */}
  {dsbPortrait?.recommendations?.length > 0 && (
    <div className="px-2 space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <Compass size={10} className="text-white/20" />
        <span className="text-[9px] font-bold text-white/25 uppercase tracking-[0.2em]">
          Рекомендации
        </span>
      </div>
      {dsbPortrait.recommendations
        .sort((a: any, b: any) => INFLUENCE_SORT[a.influence_level] - INFLUENCE_SORT[b.influence_level])
        .map((r: any) => (
          <div key={r.id} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
            <DSBInfluenceDot level={r.influence_level} />
            <p className="text-[12px] text-white/60 leading-relaxed font-light flex-1">
              {r.recommendation}
            </p>
          </div>
        ))}
    </div>
  )}

  {/* ═══ Теневой аудит ═══ */}
  {dsbPortrait?.shadows?.length > 0 && (
    <div className="px-2 space-y-2 pb-4">
      <div className="flex items-center gap-2 mb-1">
        <AlertCircle size={10} className="text-red-400/40" />
        <span className="text-[9px] font-bold text-red-400/40 uppercase tracking-[0.2em]">
          Теневой аудит
        </span>
      </div>
      {dsbPortrait.shadows.map((s: any) => (
        <DSBShadowBlock key={s.id} shadow={s} />
      ))}
    </div>
  )}
</motion.div>
```

---

### 3.2 Новый стейт — добавить в MasterHubView

```tsx
// Добавить рядом с существующими useState:
const [selectedFactor, setSelectedFactor] = useState<any | null>(null);
```

```tsx
// Константа сортировки
const INFLUENCE_SORT: Record<string, number> = { high: 0, medium: 1, low: 2 };
```

---

### 3.3 Компонент: DSBFactorCard (карточка-превью фактора)

Добавить **в тот же файл** MasterHubView.tsx, в секцию суб-компонентов внизу (рядом с `SummaryTag`, `PolarityCard`):

```tsx
// ── DSB Factor Card (превью) ─────────────────────────────────────────────────

function DSBFactorCard({ factor, sphereColor, onOpen }: {
  factor: any;
  sphereColor: string;
  onOpen: () => void;
}) {
  // Первые 2 предложения для превью
  const preview = factor.light_aspect
    ? factor.light_aspect.split('.').filter((s: string) => s.trim()).slice(0, 2).join('. ') + '.'
    : factor.core_theme || "";

  return (
    <motion.div
      onClick={onOpen}
      whileTap={{ scale: 0.98 }}
      className="p-4 rounded-2xl bg-white/[0.025] border border-white/[0.06] cursor-pointer 
                 hover:bg-white/[0.04] transition-all group"
    >
      {/* Верхняя строка: бейдж + источник */}
      <div className="flex items-center justify-between mb-2">
        <DSBInfluenceBadge level={factor.influence_level} />
        <span className="text-[9px] text-white/20 font-medium">
          {DSB_SYSTEM_SHORT[factor.source_system] || factor.source_system}
        </span>
      </div>

      {/* Заголовок фактора */}
      <h4 className="text-[13px] font-bold text-white/90 leading-snug mb-1">
        {factor.position}
      </h4>

      {/* Ключевая тема */}
      {factor.core_theme && (
        <p className="text-[11px] font-medium mb-2" style={{ color: `${sphereColor}99` }}>
          {factor.core_theme}
        </p>
      )}

      {/* Превью текста */}
      <p className="text-[11px] text-white/40 leading-relaxed font-light line-clamp-3">
        {preview}
      </p>

      {/* Подробнее */}
      <div className="flex items-center gap-1 mt-3 text-[10px] text-white/20 group-hover:text-white/40 transition-colors">
        <Eye size={10} />
        <span>Подробнее</span>
      </div>
    </motion.div>
  );
}
```

---

### 3.4 Компонент: DSBInfluenceBadge

```tsx
// ── DSB Influence Badge ──────────────────────────────────────────────────────

const DSB_INFLUENCE_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  high:   { bg: "bg-red-500/10",     text: "text-red-400",     border: "border-red-500/20",     label: "Высокое" },
  medium: { bg: "bg-amber-500/10",   text: "text-amber-400",   border: "border-amber-500/20",   label: "Среднее" },
  low:    { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20", label: "Фоновое" },
};

function DSBInfluenceBadge({ level }: { level: string }) {
  const s = DSB_INFLUENCE_STYLES[level] || DSB_INFLUENCE_STYLES.medium;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold border ${s.bg} ${s.text} ${s.border}`}>
      <span className={`w-1 h-1 rounded-full ${
        level === 'high' ? 'bg-red-400' : level === 'medium' ? 'bg-amber-400' : 'bg-emerald-400'
      }`} />
      {s.label}
    </span>
  );
}

function DSBInfluenceDot({ level }: { level: string }) {
  const color = level === 'high' ? 'bg-red-400' : level === 'medium' ? 'bg-amber-400' : 'bg-emerald-400';
  return <span className={`w-1.5 h-1.5 rounded-full ${color} flex-shrink-0 mt-1.5`} />;
}
```

---

### 3.5 Компонент: DSBPatternBlock

```tsx
// ── DSB Pattern Block (аккордеон) ────────────────────────────────────────────

function DSBPatternBlock({ pattern }: { pattern: any }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3 text-left"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <DSBInfluenceDot level={pattern.influence_level || "medium"} />
          <span className="text-[12px] font-bold text-white/80 truncate">
            {pattern.pattern_name}
          </span>
        </div>
        <motion.div animate={{ rotate: open ? 180 : 0 }} className="text-white/20 flex-shrink-0">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </motion.div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2">
              {/* Формула */}
              {pattern.formula && (
                <div className="text-[10px] text-white/30 font-mono bg-white/[0.03] rounded-lg px-2.5 py-1.5">
                  {pattern.formula}
                </div>
              )}
              {/* Описание */}
              <p className="text-[11px] text-white/50 leading-relaxed font-light">
                {pattern.description}
              </p>
              {/* Convergence */}
              {pattern.convergence_score > 0 && (
                <div className="flex items-center gap-2 pt-1">
                  <div className="flex-1 h-1 rounded-full bg-white/[0.06]">
                    <div
                      className={`h-full rounded-full ${
                        pattern.convergence_score >= 0.85 ? 'bg-red-400' :
                        pattern.convergence_score >= 0.6 ? 'bg-amber-400' : 'bg-emerald-400'
                      }`}
                      style={{ width: `${pattern.convergence_score * 100}%` }}
                    />
                  </div>
                  <span className="text-[9px] text-white/25">
                    {Math.round(pattern.convergence_score * 100)}%
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

---

### 3.6 Компонент: DSBShadowBlock

```tsx
// ── DSB Shadow Audit Block ───────────────────────────────────────────────────

function DSBShadowBlock({ shadow }: { shadow: any }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl bg-red-500/[0.03] border border-red-500/10 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3 text-left"
      >
        <span className="text-[12px] font-bold text-red-300/80 flex-1 truncate">
          {shadow.risk_name}
        </span>
        <motion.div animate={{ rotate: open ? 180 : 0 }} className="text-red-400/30 flex-shrink-0 ml-2">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </motion.div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2">
              <p className="text-[11px] text-white/40 leading-relaxed font-light">
                {shadow.description}
              </p>
              {/* Антидот */}
              <div className="rounded-lg bg-emerald-500/[0.05] border border-emerald-500/10 p-2.5">
                <span className="text-[9px] font-bold text-emerald-400/70 uppercase tracking-wider">
                  Антидот
                </span>
                <p className="text-[11px] text-white/50 leading-relaxed font-light mt-1">
                  {shadow.antidote}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

---

### 3.7 Модал: DSBFactorDetail (провал в фактор)

Добавить **после** `{/* ── Tooltip Overlay ── */}` в MasterHubView.tsx (рядом с существующим модалом activeTooltip):

```tsx
{/* ── DSB Factor Detail Modal ── */}
<AnimatePresence>
  {selectedFactor && (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={() => setSelectedFactor(null)}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
      />
      <motion.div
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 200 }}
        className="fixed inset-x-0 bottom-0 top-12 z-[101] overflow-y-auto"
        style={{ background: "var(--bg-deep)", borderTop: "1px solid rgba(255,255,255,0.1)", borderRadius: "24px 24px 0 0" }}
      >
        <div className="px-5 pt-4 pb-16">
          {/* Drag handle */}
          <div className="w-12 h-1.5 bg-white/10 rounded-full mx-auto mb-5" />

          {/* Кнопка закрыть */}
          <button
            onClick={() => setSelectedFactor(null)}
            className="flex items-center gap-2 text-white/40 text-[10px] font-bold uppercase tracking-widest mb-4"
          >
            <ArrowLeft size={14} /> Назад к сфере
          </button>

          {/* Бейдж + источник */}
          <div className="flex items-center gap-2 mb-3">
            <DSBInfluenceBadge level={selectedFactor.influence_level} />
            <span className="text-[10px] text-white/25 px-2 py-0.5 rounded-full bg-white/[0.04]">
              {DSB_SYSTEM_SHORT[selectedFactor.source_system] || selectedFactor.source_system}
            </span>
          </div>

          {/* Заголовок */}
          <h2 className="text-lg font-bold text-white tracking-tight mb-4">
            {selectedFactor.position}
          </h2>

          {/* Ключевая тема */}
          {selectedFactor.core_theme && (
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] mb-5">
              <p className="text-[13px] text-white/70 font-medium">
                {selectedFactor.core_theme}
              </p>
            </div>
          )}

          {/* ═══ Свет ═══ */}
          {selectedFactor.light_aspect && (
            <DSBDetailSection
              icon="☀️"
              title="Свет — Дар"
              text={selectedFactor.light_aspect}
              colorClass="emerald"
            />
          )}

          {/* ═══ Тень ═══ */}
          {selectedFactor.shadow_aspect && (
            <DSBDetailSection
              icon="🌑"
              title="Тень — Ловушка"
              text={selectedFactor.shadow_aspect}
              colorClass="red"
            />
          )}

          {/* ═══ Энергия ═══ */}
          {selectedFactor.energy_description && (
            <DSBDetailSection
              icon="⚡"
              title="Энергия"
              text={selectedFactor.energy_description}
              colorClass="amber"
            />
          )}

          {/* ═══ Задача развития ═══ */}
          {selectedFactor.developmental_task && (
            <DSBDetailSection
              icon="🎯"
              title="Задача развития"
              text={selectedFactor.developmental_task}
              colorClass="blue"
            />
          )}

          {/* ═══ Ключ интеграции ═══ */}
          {selectedFactor.integration_key && (
            <DSBDetailSection
              icon="🔑"
              title="Ключ к интеграции"
              text={selectedFactor.integration_key}
              colorClass="violet"
            />
          )}

          {/* ═══ Триггеры ═══ */}
          {selectedFactor.triggers?.length > 0 && (
            <div className="mt-5">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle size={12} className="text-red-400/50" />
                <span className="text-[10px] font-bold text-white/30 uppercase tracking-wider">
                  Что активирует тень
                </span>
              </div>
              <div className="space-y-1.5">
                {selectedFactor.triggers.map((t: string, i: number) => (
                  <div key={i} className="flex items-start gap-2 text-[11px] text-white/40 font-light">
                    <span className="text-red-400/50 mt-0.5 flex-shrink-0">•</span>
                    <span className="leading-relaxed">{t}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ═══ Тайминг ═══ */}
          {selectedFactor.timing && (
            <div className="mt-5 p-3 rounded-xl bg-blue-500/[0.05] border border-blue-500/10">
              <div className="flex items-center gap-1.5 mb-1">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-blue-400/60">
                  <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
                <span className="text-[9px] font-bold text-blue-300/60 uppercase tracking-wider">
                  Временной аспект
                </span>
              </div>
              <p className="text-[11px] text-white/50 font-light leading-relaxed">
                {selectedFactor.timing}
              </p>
            </div>
          )}

          {/* ═══ Связанные сферы ═══ */}
          {selectedFactor.spheres_affected?.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-1.5">
              {selectedFactor.spheres_affected.map((s: number) => {
                const meta = SPHERES_META[s - 1];
                return meta ? (
                  <span
                    key={s}
                    className="text-[9px] px-2.5 py-1 rounded-full border font-medium"
                    style={{
                      backgroundColor: `${meta.color}08`,
                      borderColor: `${meta.color}20`,
                      color: `${meta.color}90`,
                    }}
                  >
                    {meta.name}
                  </span>
                ) : null;
              })}
            </div>
          )}
        </div>
      </motion.div>
    </>
  )}
</AnimatePresence>
```

---

### 3.8 Компонент: DSBDetailSection (блок внутри детали)

```tsx
// ── DSB Detail Section ───────────────────────────────────────────────────────

const DSB_SECTION_COLORS: Record<string, { bg: string; border: string; title: string }> = {
  emerald: { bg: "bg-emerald-500/[0.04]", border: "border-emerald-500/10", title: "text-emerald-300/80" },
  red:     { bg: "bg-red-500/[0.04]",     border: "border-red-500/10",     title: "text-red-300/80" },
  amber:   { bg: "bg-amber-500/[0.04]",   border: "border-amber-500/10",   title: "text-amber-300/80" },
  blue:    { bg: "bg-blue-500/[0.04]",    border: "border-blue-500/10",    title: "text-blue-300/80" },
  violet:  { bg: "bg-violet-500/[0.04]",  border: "border-violet-500/10",  title: "text-violet-300/80" },
};

function DSBDetailSection({ icon, title, text, colorClass }: {
  icon: string;
  title: string;
  text: string;
  colorClass: keyof typeof DSB_SECTION_COLORS;
}) {
  const c = DSB_SECTION_COLORS[colorClass];

  return (
    <div className={`mt-4 rounded-xl ${c.bg} border ${c.border} p-4`}>
      <div className={`flex items-center gap-1.5 mb-2 ${c.title}`}>
        <span className="text-sm">{icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider">{title}</span>
      </div>
      <p className="text-[12px] text-white/60 leading-relaxed font-light whitespace-pre-line">
        {text}
      </p>
    </div>
  );
}
```

---

### 3.9 Константы DSB

```tsx
// Добавить в начало MasterHubView.tsx рядом с другими константами:

const DSB_SYSTEM_SHORT: Record<string, string> = {
  western_astrology: "Астрология",
  vedic_astrology: "Джйотиш",
  human_design: "Human Design",
  gene_keys: "Gene Keys",
  numerology: "Нумерология",
  matrix_of_destiny: "Матрица Судьбы",
  bazi: "Ба Цзы",
  tzolkin: "Цолькин",
};
```

---

### 3.10 Формат ответа API для фронтенда

Бэкенд endpoint `GET /api/dsb/portraits/user/{userId}/sphere/{sphere}` должен возвращать:

```json
{
  "sphere": 2,
  "brief": "Ты — гора золота с замедленным зажиганием...",
  
  "factors": [
    {
      "id": "uuid",
      "position": "Близнецы на куспиде 2 дома",
      "source_system": "western_astrology",
      "influence_level": "high",
      "core_theme": "Множественные каналы дохода",
      "light_aspect": "Деньги приходят не через одно стабильное дело...[80-200 слов]",
      "shadow_aspect": "Рассеивание. Денежный фокус скачет...[80-200 слов]",
      "energy_description": "...",
      "developmental_task": "...",
      "integration_key": "...",
      "triggers": ["Конкретная ситуация 1...", "Конкретная ситуация 2..."],
      "timing": "Каждые 3-4 года пересмотр...",
      "spheres_affected": [3, 9]
    }
  ],
  
  "patterns": [
    {
      "id": "uuid",
      "pattern_name": "Прагматичный визионер",
      "formula": "Нептун (видение) + Уран (tech) + Сатурн (структура)",
      "influence_level": "high",
      "convergence_score": 0.85,
      "description": "..."
    }
  ],
  
  "recommendations": [
    {
      "id": "uuid",
      "recommendation": "Минимум 2-3 параллельных потока дохода",
      "influence_level": "high"
    }
  ],
  
  "shadows": [
    {
      "id": "uuid",
      "risk_name": "Самообман в финансовых прогнозах",
      "description": "...",
      "convergence_score": 0.83,
      "antidote": "Внешний финансовый дашборд с реальными цифрами"
    }
  ]
}
```

---

### 3.11 Что НЕ менять

```
❌ НЕ менять шрифты — используем существующие var(--text-primary), var(--text-muted)
❌ НЕ менять page.tsx
❌ НЕ менять субтабы (personality / sides / analysis)
❌ НЕ менять грид 12 сфер в "analysis"
❌ НЕ менять header, BottomNav
❌ НЕ менять существующие стили кнопки "Назад в Океан"
❌ НЕ менять CSS-переменные
❌ НЕ удалять существующий insight фоллбэк (показывается если DSB нет)
```

### 3.12 Порядок реализации

```
1. Добавить dsbAPI в lib/api.ts                            ← 5 мин
2. Добавить константы DSB_SYSTEM_SHORT, INFLUENCE_SORT      ← 5 мин  
3. Добавить useState selectedFactor                         ← 2 мин
4. Добавить useSWR для dsbPortrait                          ← 5 мин
5. Заменить sphere detail view контент                      ← 15 мин
6. Добавить DSBFactorCard                                   ← 15 мин
7. Добавить DSBInfluenceBadge + DSBInfluenceDot             ← 5 мин
8. Добавить DSBPatternBlock                                 ← 10 мин
9. Добавить DSBShadowBlock                                  ← 10 мин
10. Добавить DSBFactorDetail (модал провала)                 ← 20 мин
11. Добавить DSBDetailSection                                ← 5 мин
12. Добавить бэкенд endpoint sphere/{N}                      ← 20 мин
                                                      ИТОГО: ~2 часа
```

---

*Патч к существующей системе DSB. Не переписывать — только добавлять.*
*Дата: 21 марта 2026*
