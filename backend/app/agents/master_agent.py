"""
Master Agent: Facade for modular specialized agents.
"""
import json
from app.config import settings
from .common import (
    client, ARCHETYPES, SPHERES, MATRIX_DATA, HAWKINS_SCALE,
    SPHERE_AGENT_STYLES, LEVEL_METHODOLOGIES, LEVEL_GOALS
)
from .sync_agent import (
    is_abstract_response, build_avatar_prompt, run_avatar_layer
)
from .hawkins_agent import (
    get_hawkins_agent_level, evaluate_hawkins
)
from .align_agent import (
    alignment_session_message, check_alignment_depth
)
from .analytic_agent import (
    run_mirror_analysis, run_alignment_expert_analysis,
    extract_sync_insights, generate_alignment_summary
)

async def analyze_reflection(text: str) -> dict:
    """
    Deep analysis of user reflection (diary entry / daily check-in).
    Extracts vibration (Hawkins), Sphere, and Archetypal resonance.
    """
    if not text:
        return {}

    prompt = f"""Ты — ИИ-аналитик системы AVATAR. Твоя задача — проанализировать ежедневную рефлексию пользователя.
Определи его текущий уровень по шкале Хокинса, выдели сферу жизни, о которой он пишет, и наиболее резонирующий архетип.

ТЕКСТ РЕФЛЕКСИИ:
"{text}"

СПИСОК СФЕР: IDENTITY, MONEY, RELATIONS, FAMILY, MISSION, HEALTH, SOCIETY, SPIRIT.
СПИСОК АРХЕТИПОВ: {[{'id': a['id'], 'name': a['name']} for a in ARCHETYPES.values()]}

ИНСТРУКЦИЯ:
1. Оцени вибрационный уровень (20-1000).
2. Выбери наиболее подходящую сферу из списка. Если неясно — IDENTITY.
3. Выбери ID архетипа, который наиболее проявлен в тексте (теневой или светлый).
4. Напиши "ai_analysis" — короткий (2-3 предложения), глубокий инсайт или поддержку.

Отвечай строго в JSON:
{{
  "hawkins_score": int,
  "hawkins_level": "название уровня",
  "sphere": "CODE",
  "archetype_id": int,
  "dominant_emotion": "эмоция",
  "ai_analysis": "текст анализа"
}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_FAST,
        messages=[{"role": "system", "content": "Система анализа рефлексий AVATAR."},
                  {"role": "user", "content": prompt}],
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "hawkins_score": 200,
            "hawkins_level": "Ок",
            "sphere": "IDENTITY",
            "archetype_id": 0,
            "dominant_emotion": "нейтральность",
            "ai_analysis": "Спасибо за вашу рефлексию."
        }
