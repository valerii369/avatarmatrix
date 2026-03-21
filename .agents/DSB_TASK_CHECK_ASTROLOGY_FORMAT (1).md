# ЗАДАЧА: Проверка и доведение формата выдачи астрологических данных до эталона

## Контекст

У нас есть система Digital Soul Blueprint (DSB). БД-схема создана (`001_dsb_tables.sql`), модели описаны в `models.py`. Сейчас нужно убедиться, что пайплайн **реально выдаёт данные в нужном формате и с нужной глубиной**. Не абстрактно — а проверить на конкретной тестовой карте и довести до эталона.

**Активное учение:** только `western_astrology`.

---

## Тестовая карта

```
Дата: 02.07.1988
Время: 00:40
Место: Тернополь, Украина (49.5535° N, 25.5948° E)
Timezone: UTC+4 (летнее время СССР 1988)
```

---

## ЧТО СДЕЛАТЬ

### Шаг 1: Написать интеграционный тест `test_portrait_quality.py`

Создай файл `backend/tests/test_portrait_quality.py` который прогоняет полный пайплайн на тестовой карте и проверяет ВСЁ нижеперечисленное.

---

### Шаг 2: Проверить выход калькулятора (Слой 1)

После запуска калькулятора западной астрологии для тестовой карты, проверь что JSON содержит:

```python
def test_calculator_planets():
    """Калькулятор должен вернуть 14 объектов с корректными данными."""
    result = await western_astrology_calculator.calculate(test_birth_data)
    planets = result["planets"]
    
    # 14 объектов обязательно
    assert len(planets) >= 14
    
    # Проверка ключевых позиций
    sun = find_planet(planets, "Sun")
    assert sun["house"] == 10
    assert 294 < sun["degree"] < 296  # ~294.951
    
    mercury = find_planet(planets, "Mercury")
    assert mercury["retrograde"] == True
    assert mercury["house"] == 9
    assert mercury["sign"] == "Capricorn"
    
    venus = find_planet(planets, "Venus")
    assert venus["retrograde"] == True
    
    jupiter = find_planet(planets, "Jupiter")
    assert jupiter["retrograde"] == True
    assert jupiter["dignity"] == "exaltation"
    
    saturn = find_planet(planets, "Saturn")
    assert saturn["dignity"] == "domicile"
    assert saturn["house"] == 10
    
    pluto = find_planet(planets, "Pluto")
    assert pluto["dignity"] == "domicile"
    assert pluto["is_stationary"] == True
    assert pluto["house"] == 7

def test_calculator_aspects():
    """Минимум 30 аспектов, ключевые точные аспекты присутствуют."""
    result = await western_astrology_calculator.calculate(test_birth_data)
    aspects = result["aspects"]
    
    assert len(aspects) >= 30
    
    # Самый точный аспект карты: Сатурн секстиль Плутон 0.13°
    saturn_pluto = find_aspect(aspects, "Saturn", "Pluto", "sextile")
    assert saturn_pluto is not None
    assert saturn_pluto["orb"] < 0.5
    assert saturn_pluto["is_exact"] == True
    
    # Уран конъюнкция Колесо Фортуны 0.62°
    uranus_fortune = find_aspect(aspects, "Uranus", "PartFortune", "conjunction")
    assert uranus_fortune is not None
    assert uranus_fortune["is_exact"] == True
    
    # Плутон квадрат Узлы 0.85°
    pluto_node = find_aspect(aspects, "Pluto", "TrueNode", "square")
    assert pluto_node is not None
    assert pluto_node["is_exact"] == True

def test_calculator_structure():
    """Стеллиумы, полусферы, ASC/MC."""
    result = await western_astrology_calculator.calculate(test_birth_data)
    
    # ASC
    assert result["ascendant"]["sign"] == "Taurus"
    assert 44 < result["ascendant"]["degree"] < 46
    
    # Стеллиумы
    stelliums = result["stelliums"]
    house_10_stellium = [s for s in stelliums if s.get("target") == 10 and s["type"] == "house"]
    assert len(house_10_stellium) == 1
    assert "Sun" in house_10_stellium[0]["planets"]
    assert "Saturn" in house_10_stellium[0]["planets"]
    
    # Полусферы
    assert result["technical_summary"]["hemispheres"]["horizontal"]["South"] >= 7
```

---

### Шаг 3: Проверить выход агента интерпретации (Слой 2)

Это **главная проверка**. Агент `WesternAstrologyAgent` должен из сырого JSON породить 40-80 объектов `UniversalInsightSchema`. Проверяем:

```python
def test_agent_quantity():
    """40-80 UIS объектов."""
    raw = await western_astrology_calculator.calculate(test_birth_data)
    insights = await western_astrology_agent.interpret(raw)
    assert 40 <= len(insights) <= 80

def test_agent_sphere_coverage():
    """Каждая из 12 сфер должна иметь минимум 2 UIS."""
    raw = await western_astrology_calculator.calculate(test_birth_data)
    insights = await western_astrology_agent.interpret(raw)
    
    sphere_counts = {}
    for i in insights:
        s = i.primary_sphere
        sphere_counts[s] = sphere_counts.get(s, 0) + 1
    
    for sphere in range(1, 13):
        assert sphere_counts.get(sphere, 0) >= 2, \
            f"Сфера {sphere} имеет {sphere_counts.get(sphere, 0)} UIS, нужно минимум 2"

def test_agent_influence_distribution():
    """Не всё HIGH. Должно быть распределение."""
    raw = await western_astrology_calculator.calculate(test_birth_data)
    insights = await western_astrology_agent.interpret(raw)
    
    levels = [i.influence_level for i in insights]
    high_count = levels.count("high")
    medium_count = levels.count("medium")
    low_count = levels.count("low")
    
    # HIGH не больше 50% от общего
    assert high_count / len(levels) < 0.5, \
        f"Слишком много HIGH: {high_count}/{len(levels)}"
    # Все три уровня представлены
    assert medium_count > 0
    assert low_count > 0

def test_agent_text_quality():
    """Тексты достаточно подробные."""
    raw = await western_astrology_calculator.calculate(test_birth_data)
    insights = await western_astrology_agent.interpret(raw)
    
    for i in insights:
        # light_aspect: минимум 3 предложения (считаем по точкам)
        if i.light_aspect:
            sentences = [s.strip() for s in i.light_aspect.split('.') if s.strip()]
            assert len(sentences) >= 3, \
                f"light_aspect слишком короткий для '{i.position}': {len(sentences)} предложений"
        
        # shadow_aspect: минимум 3 предложения
        if i.shadow_aspect:
            sentences = [s.strip() for s in i.shadow_aspect.split('.') if s.strip()]
            assert len(sentences) >= 3, \
                f"shadow_aspect слишком короткий для '{i.position}': {len(sentences)} предложений"
        
        # triggers: конкретные, не пустые
        if i.triggers:
            for t in i.triggers:
                assert len(t) > 20, \
                    f"Триггер слишком абстрактный: '{t}' (для {i.position})"
        
        # Нет запрещённых слов
        forbidden = ["в целом", "в общем", "как правило", "обычно"]
        full_text = f"{i.light_aspect} {i.shadow_aspect}"
        for word in forbidden:
            assert word not in full_text.lower(), \
                f"Запрещённое слово '{word}' в UIS для '{i.position}'"

def test_agent_key_elements_present():
    """Ключевые элементы карты не пропущены."""
    raw = await western_astrology_calculator.calculate(test_birth_data)
    insights = await western_astrology_agent.interpret(raw)
    
    positions = [i.position for i in insights]
    positions_lower = " ".join(positions).lower()
    
    # Управитель 2 дома (Меркурий) должен быть интерпретирован для сферы денег
    money_insights = [i for i in insights if i.primary_sphere == 2]
    money_positions = " ".join([i.position for i in money_insights]).lower()
    assert "mercury" in money_positions or "меркурий" in money_positions, \
        "Меркурий как управитель 2 дома не найден в сфере Деньги"
    
    # Точнейший аспект (Сатурн секстиль Плутон 0.13°) ОБЯЗАН быть
    assert any("saturn" in p.lower() and "pluto" in p.lower() for p in positions), \
        "Сатурн-Плутон секстиль (точнейший аспект) не интерпретирован"
    
    # Уран конъюнкция Фортуна (точный)
    assert any("uran" in p.lower() and "fortun" in p.lower() for p in positions), \
        "Уран-Фортуна конъюнкция не интерпретирована"
    
    # Стеллиум в 10 доме
    assert any("stellium" in p.lower() or "стеллиум" in p.lower() for p in positions), \
        "Стеллиум в 10 доме не интерпретирован"
    
    # ASC
    assert any("asc" in p.lower() or "тел" in p.lower() for p in positions), \
        "ASC Телец не интерпретирован"

def test_agent_sphere_mapping_correctness():
    """Проверка что primary_sphere маппится правильно."""
    raw = await western_astrology_calculator.calculate(test_birth_data)
    insights = await western_astrology_agent.interpret(raw)
    
    for i in insights:
        pos = i.position.lower()
        
        # Плутон в 7 доме → primary_sphere должен быть 7
        if "pluto" in pos and "7" in pos and "house" in pos:
            assert i.primary_sphere == 7, \
                f"Плутон в 7 доме маппится в сферу {i.primary_sphere}, ожидалось 7"
        
        # Марс в 8 доме → primary_sphere 8
        if "mars" in pos and "8" in pos and "house" in pos:
            assert i.primary_sphere == 8, \
                f"Марс в 8 доме маппится в сферу {i.primary_sphere}, ожидалось 8"
```

---

### Шаг 4: Проверить Sphere Agent (Слой 3) — на примере Сферы 2 (Деньги)

```python
def test_sphere_agent_layer1_depth():
    """Слой 1 (факторы): минимум 8, каждый 5+ предложений."""
    # Прогоняем полный пайплайн до Sphere Agent для сферы 2
    sphere_result = await run_pipeline_for_sphere(test_birth_data, sphere=2)
    
    factors = sphere_result["layer1_atomic_factors"]
    assert len(factors) >= 8, f"Мало факторов в сфере Деньги: {len(factors)}"
    
    for f in factors:
        desc = f.get("description", "")
        sentences = [s.strip() for s in desc.split('.') if s.strip()]
        assert len(sentences) >= 5, \
            f"Фактор '{f.get('name', '?')}' слишком сжатый: {len(sentences)} предложений, нужно 5+"
        
        # Есть метка влияния
        assert f.get("influence_level") in ("high", "medium", "low"), \
            f"Фактор '{f.get('name', '?')}' без метки влияния"

def test_sphere_agent_layer1_key_factors():
    """Ключевые факторы для сферы Деньги присутствуют."""
    sphere_result = await run_pipeline_for_sphere(test_birth_data, sphere=2)
    factors = sphere_result["layer1_atomic_factors"]
    all_text = " ".join([f.get("name", "") + " " + f.get("description", "") for f in factors]).lower()
    
    # Близнецы на 2 доме
    assert "близнец" in all_text or "gemini" in all_text, \
        "Близнецы на куспиде 2 дома не найдены в факторах сферы Деньги"
    
    # Меркурий как управитель
    assert "меркурий" in all_text or "mercury" in all_text, \
        "Меркурий (управитель 2 дома) не найден в факторах сферы Деньги"
    
    # Уран + Колесо Фортуны
    assert ("уран" in all_text or "uranus" in all_text) and ("фортун" in all_text or "fortune" in all_text), \
        "Уран ☌ Колесо Фортуны не найден в факторах сферы Деньги"

def test_sphere_agent_layer2_chains():
    """Слой 2 (цепочки): минимум 3, с convergence_score."""
    sphere_result = await run_pipeline_for_sphere(test_birth_data, sphere=2)
    chains = sphere_result["layer2_aspect_chains"]
    
    assert len(chains) >= 3, f"Мало цепочек: {len(chains)}"
    
    for c in chains:
        assert 0.0 <= c.get("convergence_score", -1) <= 1.0, \
            f"convergence_score невалиден: {c.get('convergence_score')}"
        desc = c.get("description", "")
        sentences = [s.strip() for s in desc.split('.') if s.strip()]
        assert len(sentences) >= 3, \
            f"Цепочка '{c.get('chain_name', '?')}' описание слишком короткое"

def test_sphere_agent_layer3_patterns():
    """Слой 3 (паттерны): минимум 3, с формулой и описанием."""
    sphere_result = await run_pipeline_for_sphere(test_birth_data, sphere=2)
    patterns = sphere_result["layer3_patterns"]
    
    assert len(patterns) >= 3, f"Мало паттернов: {len(patterns)}"
    
    for p in patterns:
        assert p.get("pattern_name"), "Паттерн без названия"
        assert p.get("formula"), "Паттерн без формулы"
        assert len(p.get("description", "")) > 100, \
            f"Паттерн '{p.get('pattern_name')}' описание слишком короткое"

def test_sphere_agent_layer4_recommendations():
    """Слой 4 (рекомендации): минимум 8, конкретные."""
    sphere_result = await run_pipeline_for_sphere(test_birth_data, sphere=2)
    recs = sphere_result["layer4_recommendations"]
    
    assert len(recs) >= 8, f"Мало рекомендаций: {len(recs)}"
    
    for r in recs:
        assert len(r.get("recommendation", "")) > 30, \
            f"Рекомендация слишком абстрактная: '{r.get('recommendation', '')[:50]}'"
        assert r.get("influence_level") in ("high", "medium", "low")

def test_sphere_agent_layer5_shadows():
    """Слой 5 (теневой аудит): минимум 4, с антидотами."""
    sphere_result = await run_pipeline_for_sphere(test_birth_data, sphere=2)
    shadows = sphere_result["layer5_shadow_audit"]
    
    assert len(shadows) >= 4, f"Мало рисков: {len(shadows)}"
    
    for s in shadows:
        assert s.get("risk_name"), "Риск без названия"
        assert s.get("antidote"), "Риск без антидота"
        assert len(s.get("antidote", "")) > 20, \
            f"Антидот слишком абстрактный: '{s.get('antidote', '')[:50]}'"
```

---

### Шаг 5: Проверить краткий формат и мета-паттерны

```python
def test_compressor_brief_format():
    """Краткий формат: 3-5 предложений на сферу."""
    portrait = await run_full_pipeline(test_birth_data)
    summaries = portrait["summaries"]
    
    # 12 сфер + 1 overall = 13
    assert len(summaries) == 13
    
    for s in summaries:
        text = s["brief_text"]
        sentences = [x.strip() for x in text.split('.') if x.strip()]
        assert 3 <= len(sentences) <= 7, \
            f"Сфера {s.get('sphere', 'overall')}: {len(sentences)} предложений (нужно 3-5)"
        assert len(text) > 100, \
            f"Сфера {s.get('sphere', 'overall')}: слишком коротко ({len(text)} символов)"

def test_meta_agent_patterns():
    """Meta Agent: минимум 2 суперпаттерна, каждый связывает 3+ сфер."""
    portrait = await run_full_pipeline(test_birth_data)
    meta = portrait["meta_patterns"]
    
    assert len(meta) >= 2, f"Мало мета-паттернов: {len(meta)}"
    
    for m in meta:
        assert len(m.get("spheres_involved", [])) >= 3, \
            f"Мета-паттерн '{m.get('pattern_name')}' связывает меньше 3 сфер"
        assert len(m.get("description", "")) > 100
```

---

### Шаг 6: Проверить что данные реально легли в БД

```python
def test_db_storage_completeness():
    """После пайплайна все таблицы заполнены."""
    portrait_id = await run_full_pipeline_and_save(test_birth_data)
    
    # Проверяем количества
    facts_count = await db.fetchval(
        "SELECT count(*) FROM dsb_portrait_facts WHERE portrait_id = $1", portrait_id)
    chains_count = await db.fetchval(
        "SELECT count(*) FROM dsb_portrait_aspect_chains WHERE portrait_id = $1", portrait_id)
    patterns_count = await db.fetchval(
        "SELECT count(*) FROM dsb_portrait_patterns WHERE portrait_id = $1", portrait_id)
    recs_count = await db.fetchval(
        "SELECT count(*) FROM dsb_portrait_recommendations WHERE portrait_id = $1", portrait_id)
    shadows_count = await db.fetchval(
        "SELECT count(*) FROM dsb_portrait_shadow_audit WHERE portrait_id = $1", portrait_id)
    meta_count = await db.fetchval(
        "SELECT count(*) FROM dsb_portrait_meta_patterns WHERE portrait_id = $1", portrait_id)
    summaries_count = await db.fetchval(
        "SELECT count(*) FROM dsb_portrait_summaries WHERE portrait_id = $1", portrait_id)
    
    assert 40 <= facts_count <= 80, f"facts: {facts_count}"
    assert 20 <= chains_count <= 50, f"chains: {chains_count}"
    assert 25 <= patterns_count <= 60, f"patterns: {patterns_count}"
    assert 50 <= recs_count <= 120, f"recs: {recs_count}"
    assert 20 <= shadows_count <= 50, f"shadows: {shadows_count}"
    assert 2 <= meta_count <= 8, f"meta: {meta_count}"
    assert summaries_count == 13, f"summaries: {summaries_count} (ожидалось 13)"
    
    # source_system везде western_astrology
    wrong_system = await db.fetchval(
        "SELECT count(*) FROM dsb_portrait_facts WHERE portrait_id = $1 AND source_system != 'western_astrology'",
        portrait_id)
    assert wrong_system == 0, f"Есть записи с неправильным source_system: {wrong_system}"
    
    # systems_used в портрете
    systems = await db.fetchval(
        "SELECT systems_used FROM dsb_digital_portraits WHERE id = $1", portrait_id)
    assert systems == ["western_astrology"]

def test_db_embeddings_generated():
    """Embeddings сгенерированы для всех записей."""
    portrait_id = await run_full_pipeline_and_save(test_birth_data)
    
    null_embeddings = await db.fetchval("""
        SELECT count(*) FROM dsb_portrait_facts 
        WHERE portrait_id = $1 AND embedding IS NULL
    """, portrait_id)
    assert null_embeddings == 0, f"{null_embeddings} фактов без embedding"

def test_semantic_search():
    """Semantic search возвращает релевантные результаты."""
    portrait_id = await run_full_pipeline_and_save(test_birth_data)
    
    results = await search_portrait(portrait_id, "почему мне сложно с деньгами", top_k=5)
    
    assert len(results) >= 3, "Поиск вернул мало результатов"
    
    # Хотя бы 2 из 5 результатов — из сферы 2 (Деньги)
    money_results = [r for r in results if r.get("sphere") == 2]
    assert len(money_results) >= 2, \
        f"Из 5 результатов только {len(money_results)} про деньги (сфера 2)"
```

---

### Шаг 7: Проверить промпт Sphere Agent — НЕ сжимает

Это **критическая проверка**. Наш главный страх — LLM сожмёт детальное описание в одну строку.

```python
def test_sphere_agent_does_not_compress():
    """
    КРИТИЧЕСКИЙ ТЕСТ.
    Sphere Agent НЕ ДОЛЖЕН сжимать факторы в 1-2 предложения.
    Каждый фактор = 5-15 предложений подробного описания.
    
    Антипаттерн (ПРОВАЛ):
    "Близнецы на 2 доме — многообразие финансовых каналов."
    
    Эталон (ПРАВИЛЬНО):
    "Деньги приходят не через одно стабильное дело, а через множество каналов 
    одновременно. Это человек, у которого в идеале 2-3 источника дохода. 
    Близнецы не терпят монотонности — если доход завязан на одном повторяющемся 
    процессе, мотивация падает и деньги сохнут. Конкретные денежные каналы: 
    продажа информации, консалтинг, обучение, медиа, контент, посредничество.
    Теневая сторона: рассеивание фокуса, начал один проект — переключился..."
    """
    sphere_result = await run_pipeline_for_sphere(test_birth_data, sphere=2)
    factors = sphere_result["layer1_atomic_factors"]
    
    short_factors = []
    for f in factors:
        desc = f.get("description", "")
        word_count = len(desc.split())
        if word_count < 50:  # Меньше 50 слов = сжато
            short_factors.append({
                "name": f.get("name", "?"),
                "word_count": word_count,
                "text_preview": desc[:100]
            })
    
    assert len(short_factors) == 0, \
        f"ПРОВАЛ: {len(short_factors)} факторов сжаты (< 50 слов):\n" + \
        "\n".join([f"  - {sf['name']}: {sf['word_count']} слов: '{sf['text_preview']}...'" 
                   for sf in short_factors])
```

---

## ЭТАЛОН: Как ДОЛЖЕН выглядеть фактор в Сфере 2

Для сравнения с тем, что выдаёт система. Если система выдаёт значительно короче — нужно править промпт Sphere Agent.

### ПРАВИЛЬНО (эталон):

```
ФАКТОР: Близнецы на куспиде 2 дома (Западная астрология)
Влияние: 🔴 HIGH

Деньги приходят не через одно стабильное дело, а через множество каналов 
одновременно. Это человек, у которого в идеале 2-3 источника дохода, а не один. 
Близнецы не терпят монотонности — если доход завязан на одном повторяющемся 
процессе, мотивация падает и деньги сохнут.

Конкретные денежные каналы Близнецов: продажа информации, консалтинг, обучение, 
медиа, контент, посредничество, переговоры, переводы (в широком смысле — 
перевод смыслов между системами). Торговля — но не товарами, а идеями и связями. 
Нетворкинг как прямой источник дохода: "я знаю нужного человека" = деньги.

Теневая сторона Близнецов на 2 доме: рассеивание. Денежный фокус скачет. 
Начал один проект — увидел другую возможность — переключился — ни один не дал 
полного результата. Поверхностность в монетизации: много мелких потоков, 
ни один не вырастает в серьёзную реку.
```

**Это ~150 слов. Каждый фактор должен быть в этом диапазоне (80-200 слов).**

### НЕПРАВИЛЬНО (антипаттерн):

```
ФАКТОР: Близнецы на 2 доме
Влияние: medium

Многообразие финансовых каналов, коммуникативные способности используются 
для заработка.
```

**Это 10 слов. ПРОВАЛ. Нет конкретики, нет теней, нет каналов, нет живого языка.**

---

## ЕСЛИ ТЕСТЫ ПАДАЮТ — ЧТО ЧИНИТЬ

| Проблема | Где чинить | Что делать |
|----------|-----------|------------|
| Мало UIS (< 40) | Промпт `WesternAstrologyAgent` | Добавить явное требование: "создай отдельный UIS для КАЖДОЙ планеты в доме, КАЖДОГО аспекта < 8°, КАЖДОГО стеллиума" |
| Факторы сжаты (< 50 слов) | Промпт `SphereAgent` | Добавить: "Каждый фактор: МИНИМУМ 80 слов. Описывай подробно: что конкретно означает, как проявляется в жизни, какие конкретные ситуации, теневая сторона" |
| Нет метки влияния | Промпт `WesternAstrologyAgent` | Добавить критерии: "точный аспект < 1° = high, планета в достоинстве = high, широкий аспект > 7° = low" |
| Маппинг сфер неверный | Промпт `WesternAstrologyAgent` | Добавить таблицу: "Планета в N-м доме → primary_sphere = N. Управитель N-го дома → сфера N" |
| Мало цепочек (< 3) | Промпт `SphereAgent` | Усилить секцию Слоя 2: "Найди ВСЕ связи между факторами. Если 2+ элемента указывают на одно — это цепочка" |
| Рекомендации абстрактные | Промпт `SphereAgent` | Добавить: "Каждая рекомендация = конкретное действие. Не 'будь внимательнее', а 'веди финансовый дашборд с реальными цифрами ежемесячно'" |
| Embeddings NULL | `storage/embeddings.py` | Проверить что embedding генерируется ДО вставки в БД или сразу после |
| Поиск не релевантен | `storage/search.py` | Проверить что embedding_text формируется из ключевых полей (sphere + theme + description) |

---

## ЗАПУСК

```bash
# Прогнать все тесты
cd backend
pytest tests/test_portrait_quality.py -v --tb=long

# Прогнать только критический тест на сжатие
pytest tests/test_portrait_quality.py::test_sphere_agent_does_not_compress -v

# Прогнать только проверку БД
pytest tests/test_portrait_quality.py::test_db_storage_completeness -v
```

---

*Тестовая карта: 02.07.1988, 00:40, Тернополь*
*Единственное активное учение: western_astrology*
*Дата задачи: 21 марта 2026*
