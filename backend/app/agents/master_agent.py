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
    sphere: str = Field(description="Код сферы: IDENTITY, RESOURCES, COMMUNICATION, ROOTS, CREATIVITY, SERVICE, PARTNERSHIP, TRANSFORMATION, EXPANSION, STATUS, VISION, SPIRIT.")
    archetype_id: int = Field(description="ID наиболее резонирующего архетипа.")
    dominant_emotion: str = Field(description="Доминирующая эмоция в тексте.")
    ai_analysis: str = Field(description="Короткий (2-3 предложения), глубокий инсайт или поддержка.")

async def analyze_reflection(text: str, gender: str = "не указан", language: str = "ru") -> dict:
    """
    Deep analysis of user reflection (diary entry / daily check-in).
    Extracts vibration (Hawkins), Sphere, and Archetypal resonance.
    """
    if not text:
        return {}

    prompt = f"""
    ТЫ — мудрое, эмпатичное ядро системы AVATAR. Ты помогаешь человеку осознать скрытые смыслы его состояния через его слова.
    Пол пользователя: {gender} (используй корректные окончания и стиль обращения).
    Язык: {language.upper()} (Всегда отвечай только на этом языке).
    
    ТЕКСТ РЕФЛЕКСИИ:
    "{text}"
    
    АЛГОРИТМ АНАЛИЗА:
    1. КАНАЛ СОМАТИКИ: Заметь, где в тексте проскальзывает тело (напряжение, холод, легкость, ком в горле). Тело никогда не лжет.
    2. ПАТТЕРН: Определи, в каком сценарии сейчас находится человек (борьба, заморозка, ожидание спасателя, созидание).
    3. ТОЧНАЯ КАЛИБРОВКА (ШКАЛА ХОКИНСА): 
       - Оцени вибрацию (20-1000) по самому честному маркеру. 
       - Помни про «интеллектуальный мост»: если человек много рассуждает, но не чувствует — балл не выше 400.
    4. КЛАССИФИКАЦИЯ: Определи сферу жизни (IDENTITY, RESOURCES, COMMUNICATION, ROOTS, CREATIVITY, SERVICE, PARTNERSHIP, TRANSFORMATION, EXPANSION, STATUS, VISION, SPIRIT) и резонирующий архетип.
    5. ИНСАЙТ ДЛЯ ДУШИ: Сформулируй 2-3 предложения поддержки. Это должен быть не «диагноз», а теплый, глубокий инсайт, который дает ресурс или подсвечивает выход.
    
    Отвечай строго в JSON:
    {{
      "hawkins_score": int,
      "hawkins_level": "название уровня",
      "sphere": "CODE",
      "archetype_id": int,
      "dominant_emotion": "эмоция",
      "ai_analysis": "текст анализа (твой инсайт)"
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
