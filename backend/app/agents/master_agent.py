"""
Master Agent: Facade for modular specialized agents.
"""
import json
from app.config import settings
from .common import (
    client, ARCHETYPES, SPHERES, MATRIX_DATA, HAWKINS_SCALE,
    SPHERE_AGENT_STYLES, LEVEL_METHODOLOGIES, LEVEL_GOALS
)
from .sync_agent import build_avatar_prompt
from .align_agent import alignment_session_message
from pydantic import BaseModel, Field

class ReflectionAnalysis(BaseModel):
    hawkins_score: int = Field(description="Вибрационный уровень (20-1000).")
    hawkins_level: str = Field(description="Название уровня Хокинса.")
    sphere: str = Field(description="Код сферы: IDENTITY, MONEY, RELATIONS, FAMILY, MISSION, HEALTH, SOCIETY, SPIRIT.")
    archetype_id: int = Field(description="ID наиболее резонирующего архетипа.")
    dominant_emotion: str = Field(description="Доминирующая эмоция в тексте.")
    ai_analysis: str = Field(description="Короткий (2-3 предложения), глубокий инсайт или поддержка.")

async def analyze_reflection(text: str) -> dict:
    """
    Deep analysis of user reflection (diary entry / daily check-in).
    Extracts vibration (Hawkins), Sphere, and Archetypal resonance.
    """
    if not text:
        return {}

    prompt = f"""
    ТЫ — диагностическое ядро AVATAR.
    Твоя задача: Провести глубокий психологический анализ рефлексии пользователя.
    
    ТЕКСТ РЕФЛЕКСИИ:
    "{text}"
    
    АЛГОРИТМ АНАЛИЗА:
    1. КАНАЛ ТЕЛА: Извлеки упоминания телесных ощущений (сжатие, тепло, холод, напряжение). Тело — самый достоверный маркер.
    2. КАНАЛ ОБРАЗОВ И ДЕЙСТВИЙ: Проанализируй динамику в тексте (статика/движение, открытость/замкнутость).
    3. ТОЧНАЯ КАЛИБРОВКА (ШКАЛА ХОКИНСА): 
       - Оцени балл (20-1000) по ХУДШЕМУ достоверному маркеру (диссоциация < 50, апатия 50, страх 100, гнев 150, разум 400).
       - Если есть рационализация без чувств — балл НЕ выше 400.
    4. КЛАССИФИКАЦИЯ: Определи сферу жизни (IDENTITY, MONEY, RELATIONS, FAMILY, MISSION, HEALTH, SOCIETY, SPIRIT) и резонирующий архетип.
    5. ИНСАЙТ: Сформулируй короткий, глубокий инсайт (2-3 предложения), который возвращает человека к его силе или подсвечивает паттерн.
    
    Отвечай строго в JSON:
    {{
      "hawkins_score": int,
      "hawkins_level": "название уровня",
      "sphere": "CODE",
      "archetype_id": int,
      "dominant_emotion": "эмоция",
      "ai_analysis": "текст анализа"
    }}"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_FAST,
            messages=[{"role": "system", "content": "Система анализа рефлексий AVATAR."},
                      {"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={
                "type": "json_schema", 
                "json_schema": {"name": "reflection_analysis", "schema": ReflectionAnalysis.model_json_schema()}
            }
        )
        result_data = ReflectionAnalysis.model_validate_json(response.choices[0].message.content)
        return result_data.model_dump()
    except Exception as e:
        print(f"Error in analyze_reflection: {e}")
        return {
            "hawkins_score": 200,
            "hawkins_level": "Ок",
            "sphere": "IDENTITY",
            "archetype_id": 0,
            "dominant_emotion": "нейтральность",
            "ai_analysis": "Спасибо за вашу рефлексию."
        }
