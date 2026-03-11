import json
from typing import Optional
from .common import client, settings, ARCHETYPES, SPHERES, MATRIX_DATA
from .sync_agent import build_avatar_prompt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.portrait import UserPortrait, Pattern
from app.models.sync_session import SyncSession

async def run_mirror_analysis(
    archetype_id: int,
    sphere: str,
    session_transcript: list,
    phase_data: dict = None,
    portrait_context: dict = None
) -> dict:
    """Run the final analytical 'Mirror' call."""
    prompt = build_avatar_prompt("mirror", archetype_id, sphere, {}, False, None, portrait_context)
    
    messages = [{"role": "system", "content": prompt}]
    # Format transcript for the analyst
    transcript_text = "\n".join([f"{m['role']}: {m['content']}" for m in session_transcript])
    
    user_content = f"Транскрипт сессии:\n{transcript_text}"
    if phase_data and "metrics" in phase_data:
        metrics_json = json.dumps(phase_data["metrics"], ensure_ascii=False, indent=2)
        user_content += f"\n\nМЕТРИКИ СЕССИИ (длина, тело, объекты):\n{metrics_json}"
        
    messages.append({"role": "user", "content": user_content})

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=600,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "real_picture": "Ошибка анализа",
            "core_pattern": "Не определен",
            "shadow_active": "Не определен",
            "body_anchor": "Не определен",
            "first_insight": "Не определен",
            "mental_thinking": [],
            "mental_reactions": [],
            "mental_patterns": [],
            "mental_aspirations": [],
            "hawkins_score": 100,
            "hawkins_level": "Страх"
        }

async def run_alignment_expert_analysis(
    chat_history: list[dict],
    archetype_id: int,
    sphere: str
) -> dict:
    """
    Final expert review of an Alignment Session transcript.
    Evaluates the actual transformation depth and final Hawkins state.
    """
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})
    
    transcript_text = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in chat_history])

    prompt = f"""Ты — старший аналитик системы AVATAR, эксперт по шкале Хокинса и глубинной трансформации.
Твоя задача — провести финальный аудит сессии ВЫРАВНИВАНИЯ.

Архетип: {archetype.get('name', '')} | Сфера: {sphere_data.get('name_ru', sphere)}

ТРАНСКРИПТ СЕССИИ:
{transcript_text[:5000]}

АЛГОРИТМ АУДИТА:
1. ОЦЕНКА ИСКРЕННОСТИ: Насколько ответы пользователя были формальными или они шли из чувств/тела?
2. ГЛУБИНА ПЕРЕЗАПИСИ (Слой 4): Смог ли пользователь реально увидеть и выбрать альтернативную реакцию?
3. ФИНАЛЬНЫЙ ВИБРАЦИОННЫЙ ОТКЛИК: Какое состояние зафиксировано в конце (Этап 5-6)?
4. ДИНАМИКА: С какого уровня Хокинса начали и к какому реально пришли (не верь автоматическому счетчику, замерь сам).
5. ПРАВИЛО РЕАЛИЗМА: Скачок более чем на 150 пунктов за сессию — подозрителен. Если нет описания ОСТРОГО телесного инсайта, ограничивай рост балла.
6. АНТИ-БАЙПАСИНГ: Если пользователь использует термины ("я осознал", "я в потоке"), но не описывает смену ощущений в узле тела — это интеллектуальная защита (уровень 400), а не духовный рост (уровень 500+).

Отвечай строго в JSON:
{{
  "hawkins_score": 250,
  "hawkins_level": "Смелость",
  "dominant_emotion": "решимость",
  "transformation_depth": 8,
  "final_state_summary": "краткое описание достигнутого состояния",
  "is_shadow_integrated": true
}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "hawkins_score": 100,
            "hawkins_level": "Страх",
            "dominant_emotion": "не определено",
            "transformation_depth": 1,
            "final_state_summary": "Анализ не удался",
            "is_shadow_integrated": False
        }

async def extract_sync_insights(phase_data: dict, archetype_id: int, sphere: str) -> dict:
    """
    Extract structured insights from completed sync session.
    Returns core_belief, shadow_pattern, body_anchor, tags, etc.
    """
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})

    prompt = f"""Ты — аналитик сессии глубокой синхронизации AVATAR.
Оцениваешь результаты погружения в подсознание.

Архетип: {archetype.get('name', '')} | Сфера: {sphere_data.get('name_ru', sphere)}

Транскрипт всех 5 слоев синхронизации:
{json.dumps(phase_data, ensure_ascii=False, indent=2)[:2500]}

ЗАДАЧА 1: Структурировать инсайты, фокусируясь на "Разломе" (Слой 3) и финальном "Дне" (Слой 4).
ЗАДАЧА 2: Проанализировать выборы и символы. Определи НАЙНИЗШУЮ проявленную точку по шкале Хокинса.
ЗАДАЧА 3: Проверить на "Интеллектуализацию". Если человек звучит умнее, чем чувствует его тело (по описанию), снижай балл до реального соматического уровня.

Отвечай строго в JSON формата:
{{
  "core_belief": "я не достоин финансового успеха",
  "shadow_pattern": "избегание + замирание",
  "body_anchor": "сжатие в груди",
  "projection": "зависть к успешным",
  "avoidance": "выбор безопасного пути",
  "key_choice_analysis": "анализ выбора на Разломе",
  "dominant_emotion": "страх/тревога",
  "tags": ["недостойность", "избегание", "страх_успеха", "контроль"],
  "hawkins_score": 100,
  "hawkins_level": "Страх"
}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "core_belief": "", "shadow_pattern": "", "body_anchor": "",
            "projection": "", "avoidance": "", "dominant_emotion": "",
            "tags": [], "hawkins_score": 100, "hawkins_level": "Страх"
        }

async def generate_alignment_summary(
    chat_history: list[dict],
    archetype_id: int,
    sphere: str
) -> dict:
    """
    Summarize alignment session for diary.
    Extracts: integration_plan, new_belief, final_insight.
    """
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})

    history_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in chat_history])

    prompt = f"""Ты — аналитик сессий трансформации AVATAR.
Твоя задача — подвести итог сессии выравнивания для записи в дневник.

Архетип: {archetype.get('name', '')} | Сфера: {sphere_data.get('name_ru', sphere)}

Диалог сессии:
{history_text[:4000]}

Выдели:
1. НОВОЕ УБЕЖДЕНИЕ: Короткая фраза, ставшая итогом сессии (якорь).
2. ПЛАН ВНЕДРЕНИЯ (Integration Plan): 1-3 конкретных действия в реальности на ближайшую неделю.
3. ГЛАВНЫЙ ИНСАЙТ: Глубинное осознание о работе паттерна.

Отвечай строго в JSON:
{{
  "new_belief": "я создаю свой мир через воображение",
  "integration_plan": "1. Утром визуализировать 5 минут... 2. Сказать 'нет' предложению...",
  "final_insight": "мой страх был лишь маской защиты..."
}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "new_belief": "",
            "integration_plan": "Продолжать наблюдение за собой.",
            "final_insight": ""
        }

async def extract_response_features(
    scene_text: str,
    user_response: str,
    archetype_id: Optional[int] = None,
    sphere: Optional[str] = None
) -> dict:
    """
    Module for interpreting user responses in textual diagnostic scenes.
    Converts free text into structured state features.
    """
    archetype = ARCHETYPES.get(archetype_id, {}) if archetype_id is not None else {}
    sphere_data = SPHERES.get(sphere, {}) if sphere is not None else {}

    prompt = f"""
    Ты — эксперт по анализу подсознательных проекций и поведенческих паттернов в системе AVATAR.
    Твоя задача: преобразовать свободный текст ответа пользователя в структурированные признаки состояния.

    СЦЕНА (КОНТЕКСТ):
    {scene_text}

    ОТВЕТ ПОЛЬЗОВАТЕЛЯ:
    "{user_response}"

    АРХЕТИП (Доп. контекст): {archetype.get('name', 'Не указан')}
    СФЕРА: {sphere_data.get('name_ru', 'Не указана')}

    ИЗВЛЕКИ СЛЕДУЮЩИЕ ПРИЗНАКИ (СТРОГО):
    1. ДЕЙСТВИЕ (Action): 
       - action: основной глагол действия (move_forward, stay, lookup, search, etc.)
       - pace: темп (cautious, fast, static, hesitant)
       - target: объект взаимодействия
    2. ЭМОЦИОНАЛЬНЫЙ ВЕКТОР (0.0 - 1.0):
       - calm, fear, curiosity, control, confusion, trust
    3. ПОВЕДЕНЧЕСКИЙ ПАТТЕРН (Type):
       - exploration (исследование)
       - avoidance (избегание)
       - control (контроль)
       - observation (наблюдение)
       - interaction (взаимодействие)
       - stillness (остановка/замирание)
    4. ПОЗИЦИЯ (Stance): 
       - approach, avoid, observe, control, ignore

    ВНИМАНИЕ: Не делай выводов об архетипах. Только извлечение сигналов из текста.

    Отвечай строго в формате JSON:
    {{
      "action_type": "move_forward",
      "pace": "hesitant",
      "attention_focus": "environment/self/object",
      "emotion_vector": {{
        "calm": 0.2, "fear": 0.5, "curiosity": 0.3, "control": 0.4, "confusion": 0.6, "trust": 0.1
      }},
      "behavior_pattern": "avoidance",
      "stance": "observe",
      "energy_level": 0.4,
      "risk_tolerance": "low/medium/high"
    }}
    """

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": "Ты — AI-интерпретатор поведенческих паттернов."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Feature Extraction Error: {e}")
        return {
            "action_type": "unknown",
            "pace": "unknown",
            "emotion_vector": {},
            "behavior_pattern": "unknown",
            "stance": "unknown"
        }

async def update_user_portrait(db: AsyncSession, user_id: int, session_id: int) -> dict:
    """
    Aggregates session results into a UserPortrait (Consciousness Imprint).
    Identifies cross-sphere patterns and updates the body map.
    """
    # 1. Fetch the completed session
    result = await db.execute(select(SyncSession).where(SyncSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return {}

    # 2. Find or Create UserPortrait for this sphere
    portrait_res = await db.execute(
        select(UserPortrait).where(
            UserPortrait.user_id == user_id,
            UserPortrait.sphere == session.sphere
        )
    )
    portrait = portrait_res.scalar_one_or_none()
    if not portrait:
        portrait = UserPortrait(user_id=user_id, sphere=session.sphere)
        db.add(portrait)
        await db.flush()

    # 3. Update Sphere Data
    new_card_entry = {
        "archetype_id": session.archetype_id,
        "date": "now", # Ideally use real timestamp
        "hawkins_score": session.hawkins_score,
        "core_pattern": session.core_pattern,
        "body_anchor": session.body_anchor,
        "recurring_symbol": session.recurring_symbol
    }
    
    cards_data = list(portrait.cards_data or [])
    # Update if already exists for this archetype, else append
    existing_idx = next((i for i, c in enumerate(cards_data) if c.get("archetype_id") == session.archetype_id), -1)
    if existing_idx >= 0:
        cards_data[existing_idx] = new_card_entry
    else:
        cards_data.append(new_card_entry)
    
    portrait.cards_data = cards_data
    
    # 4. Update Hawkins Stats
    timeline = list(portrait.hawkins_timeline or [])
    timeline.append({"date": "now", "score": session.hawkins_score, "archetype_id": session.archetype_id})
    portrait.hawkins_timeline = timeline[-20:] # Keep last 20
    
    portrait.avg_hawkins = int(sum(c.get("hawkins_score", 0) for c in cards_data) / len(cards_data))
    portrait.min_hawkins = min(c.get("hawkins_score", 1000) for c in cards_data)

    # 5. Update Pattern Table (Cross-sphere)
    if session.core_pattern:
        # Simple tag extraction (split by space/comma)
        tags = [t.strip().lower() for t in session.core_pattern.replace(",", " ").split() if len(t) > 3]
        for tag in tags:
            pattern_res = await db.execute(select(Pattern).where(Pattern.user_id == user_id, Pattern.tag == tag))
            pattern = pattern_res.scalar_one_or_none()
            if not pattern:
                pattern = Pattern(user_id=user_id, tag=tag)
                db.add(pattern)
                await db.flush()
            
            pattern.occurrences += 1
            cards_json = list(pattern.cards_json or [])
            if session.archetype_id not in [c.get("archetype_id") for c in cards_json]:
                cards_json.append({"archetype_id": session.archetype_id, "sphere": session.sphere, "strength": 1})
            pattern.cards_json = cards_json

    await db.commit()
    return {"status": "success", "sphere": session.sphere}
