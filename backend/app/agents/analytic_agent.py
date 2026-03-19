import json
import logging
from typing import Optional
from app.agents.common import client, settings, ARCHETYPES, SPHERES, MATRIX_DATA
from app.agents.sync_agent import build_avatar_prompt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.sync_session import SyncSession
from app.services.evolution_service import EvolutionService

logger = logging.getLogger(__name__)

async def run_mirror_analysis(
    archetype_id: int,
    sphere: str,
    session_transcript: list,
    phase_data: dict = None,
    portrait_context: dict = None,
    db: AsyncSession = None
) -> dict:
    """Run the final analytical 'Mirror' call."""
    system_prompt, layer_prompt = build_avatar_prompt("mirror", archetype_id, sphere, {}, False, None, portrait_context)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": layer_prompt}
    ]
    # Format transcript for the analyst
    transcript_text = "\n".join([f"{m['role']}: {m['content']}" for m in session_transcript])
    
    # NEW: Symbolic Intelligence Context
    symbol_context = ""
    if db:
        from app.core.symbolic_service import SymbolicService
        symbol_context = await SymbolicService.get_symbolic_context(db, portrait_context.get('user_id', 0), transcript_text, sphere)

    user_content = f"Транскрипт сессии:\n{transcript_text}\n\n{symbol_context}"
    if phase_data:
        if "metrics" in phase_data:
            metrics_json = json.dumps(phase_data["metrics"], ensure_ascii=False, indent=2)
            user_content += f"\n\nМЕТРИКИ СЕССИИ (длина, тело, объекты):\n{metrics_json}"
            
        # Hook up the new Projective Scene metadata
        scenes_data = phase_data.get("scenes", {})
        meta_blocks = []
        for layer, scene_info in scenes_data.items():
            meta = scene_info.get("meta_data")
            if meta:
                projections = json.dumps(meta.get("projection_dictionary", []), ensure_ascii=False, indent=2)
                focus = json.dumps(meta.get("diagnostic_focus", {}), ensure_ascii=False, indent=2)
                meta_blocks.append(f"СЛОЙ {layer} - Словарь проекций:\n{projections}\nДиагностический фокус:\n{focus}")
        
        if meta_blocks:
            user_content += "\n\nМЕТАДАННЫЕ ПРОЕКТИВНЫХ СЦЕН (Для экспертного анализа):\n" + "\n---\n".join(meta_blocks)

    messages.append({"role": "user", "content": user_content})

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    
    # Requirement: The analyzer must now also output a 'symbols_identified' field {symbol: interpretation}
    # This will be used to update personal symbols.
    
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
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Feature Extraction Error: {e}")
        return {
            "action_type": "unknown",
            "pace": "unknown",
            "emotion_vector": {},
            "behavior_pattern": "unknown",
            "stance": "unknown"
        }

async def update_user_portrait(db: AsyncSession, user_id: int, session_id: int) -> dict:
    """
    Records session results into User Evolution (replaces legacy UserPortrait).
    """
    # 1. Fetch the completed session
    result = await db.execute(select(SyncSession).where(SyncSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return {}

    # 2. Record session completion in Evolution
    await EvolutionService.update_session_progress(
        db=db,
        user_id=user_id,
        session_type="sync",
        progress_data={
            "session_id": session_id,
            "sphere": session.sphere,
            "archetype_id": session.archetype_id,
            "hawkins_score": session.hawkins_score,
            "core_pattern": session.core_pattern,
            "body_anchor": session.body_anchor,
            "is_complete": session.is_complete
        }
    )

    await db.commit()
    return {"status": "success", "sphere": session.sphere}
