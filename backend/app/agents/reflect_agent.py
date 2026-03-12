import json
from pydantic import BaseModel, Field
from .common import client, settings, SPHERE_AGENT_STYLES

# ---------------------------------------------------------------------
# PYDANTIC STRUCTURED OUTPUTS
# ---------------------------------------------------------------------
class ReflectionResponse(BaseModel):
    ai_response: str = Field(description="Текст ответа для пользователя (эмпатичный, 2-4 предложения). Всегда заканчивается открытым вопросом.")
    phase_complete: bool = Field(description="True, если цель текущей фазы достигнута и можно переводить юзера на следующий этап (или завершать).")
    extracted_emotion: str = Field(description="Ключевая эмоция, которую сейчас переживает юзер (например: 'Гнев', 'Тревога', 'Апатия', 'Радость', 'Инсайт').")
    hawkins_score_estimation: int = Field(default=200, description="Только для Фазы 4: Оценка уровня по шкале Хокинса от 20 до 1000. В других фазах всегда 0.")

# ---------------------------------------------------------------------
# PHASE PROMPTS
# ---------------------------------------------------------------------

PHASE_PROMPTS = {
    1: """ФАЗА 1: ВХОД И ЗАЗЕМЛЕНИЕ (Entrance).
Цель фазы: Собрать сухие факты. Вывести человека из хаоса в точку 'здесь и сейчас' (по Пеннебейкеру).
Твоя задача: Внимательно выслушать, проявить эмпатию. Задавать вопросы только о фактах. 'Что конкретно произошло?', 'Что вы услышали или увидели?'.
УСЛОВИЕ ПЕРЕХОДА (phase_complete=true): Если пользователь назвал конкретное событие или факт, а не просто абстрактно жалуется.""",
    
    2: """ФАЗА 2: СПУСК К ТЕНИ (Descent).
Цель фазы: Понять истинную боль и спуститься на уровень чувств (по Юнгу).
Твоя задача: Увести юзера от описания событий к ощущениям. 'Что вы чувствуете в теле, когда это происходит?', 'Какая самая болезненная мысль крутится в голове?'.
УСЛОВИЕ ПЕРЕХОДА (phase_complete=true): Если пользователь признался в истинной негативной/теневой эмоции (страх, вина, гнев, стыд).""",
    
    3: """ФАЗА 3: СДВИГ И ЭКСТЕРНАЛИЗАЦИЯ (Shift).
Цель фазы: Разотождествить человека с его проблемой (по М. Уайту).
Твоя задача: Показать, что 'он — не его проблема'. Задать сдвигающий вопрос. 'Чьим голосом говорит этот страх?', 'Если бы эта тревога стояла рядом с вами, как бы она выглядела?', 'Где в теле живет это убеждение, и каково оно на ощупь?'.
УСЛОВИЕ ПЕРЕХОДА (phase_complete=true): Если пользователь смог взглянуть на проблему со стороны или почувствовал облегчение/инсайт.""",
    
    4: """ФАЗА 4: ИНТЕГРАЦИЯ (Integration).
Цель фазы: Заземлить новый опыт в материю и рассчитать вибрации.
Твоя задача: Вернуть человека в реальность с новым пониманием. 'Какой один крошечный шаг в физическом мире вы готовы сделать сегодня (или прямо сейчас), исходя из этого нового состояния?'.
ОБЯЗАТЕЛЬНО: Оцени уровень вибраций пользователя по Шкале Хокинса (hawkins_score_estimation) от 20 до 1000 на основе его последнего инсайта. 
УСЛОВИЕ ПЕРЕХОДА (phase_complete=true): Если юзер назвал конкретное действие или выразил глубокое принятие."""
}

async def reflection_chat_message(
    chat_history: list[dict],
    user_message: str,
    sphere: str = "IDENTITY",
    current_phase: int = 1
) -> tuple[str, bool, dict]:
    """
    Generate structured AI response for an interactive 4-phase reflection session.
    Returns (ai_response_text, is_phase_complete, analysis_dict)
    """
    sphere_style = SPHERE_AGENT_STYLES.get(sphere, "мудрый проводник")
    
    # Safely get the phase instructions or default to Phase 1
    phase_instructions = PHASE_PROMPTS.get(current_phase, PHASE_PROMPTS[1])
    
    system_prompt = f"""Ты — ИИ-проводник системы AVATAR, специалист по глубокой рефлексии.
Твоя роль/вибрация в этом диалоге: {sphere_style}.

{phase_instructions}

ОБЩИЕ ПРАВИЛА:
- Выступай как зеркало. Не давай бытовых советов ('выпей воды, успокойся').
- Твои реплики должны быть короткими (2-4 предложения) и бить прямо в суть.
- ВСЕГДА заканчивай свою реплику ОДНИМ глубоким открытым вопросом.
- Отвечай ИСКЛЮЧИТЕЛЬНО в формате JSON согласно запрошенной схеме.
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # We don't need the entire history, just the last ~10 messages to keep focus
    messages.extend(chat_history[-10:])
    
    if user_message.strip():
        messages.append({"role": "user", "content": user_message})

    # Call LLM with Structured Outputs
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_FAST, # gpt-4o-mini is perfect for this
        messages=messages,
        temperature=0.6,
        response_format={
            "type": "json_schema", 
            "json_schema": {"name": "reflection_schema", "schema": ReflectionResponse.model_json_schema()}
        }
    )
    
    # Parse output
    try:
        raw_content = response.choices[0].message.content
        result_data = ReflectionResponse.model_validate_json(raw_content)
        
        analysis_dict = {
            "extracted_emotion": result_data.extracted_emotion,
            "hawkins_score": result_data.hawkins_score_estimation
        }
        
        return result_data.ai_response, result_data.phase_complete, analysis_dict
    except Exception as e:
        # Fallback in case of parsing error
        print(f"[Reflection Error] Failed to parse structured output: {e}\nRaw={response.choices[0].message.content}")
        return "Я слышу тебя. Попробуй погрузиться чуть глубже: что именно сейчас вызывает наибольшее сопротивление?", False, {"extracted_emotion": "Unknown", "hawkins_score": 200}
