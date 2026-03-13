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

# ---------------------------------------------------------------------
# PHASE PROMPTS (EXPERIENCED PSYCHOLOGIST MODEL)
# ---------------------------------------------------------------------

PHASE_PROMPTS = {
    1: """ФАЗА 1: ПРИСУТСТВИЕ И ВАЛИДАЦИЯ.
Твоя цель: Дать человеку почувствовать, что его слышат и принимают без условий. 
ПРАВИЛО: Не допрашивай «что случилось?». Если фактов нет, работай с состоянием. 
ВАЛИДАЦИЯ: Используй фразы, признающие тяжесть или важность момента.
УСЛОВИЕ ПЕРЕХОДА (phase_complete=true): Пользователь выразил согласие с твоим пониманием или углубился в описание своего состояния.""",
    
    2: """ФАЗА 2: ПОИСК ВНУТРЕННЕГО УЗЛА.
Твоя цель: Помочь увидеть скрытый механизм или старую защитную реакцию.
ТАКТИКА: Предложи мягкую гипотезу. «Похоже, эта реакция когда-то помогала вам выжить/справиться, но сейчас она забирает слишком много сил».
УСЛОВИЕ ПЕРЕХОДА (phase_complete=true): Пользователь осознал связь текущего состояния со старым паттерном или выразил готовность посмотреть на это иначе.""",
    
    3: """ФАЗА 3: СДВИГ (РЕФРЕЙМИНГ).
Твоя цель: Создать «трещину» в привычном восприятии. Предложить новую перспективу.
ТАКТИКА: Используй парадоксальные вопросы или переосмысление ситуации. «А что, если этот страх — не враг, а очень уставший страж, которому пора в отпуск?».
УСЛОВИЕ ПЕРЕХОДА (phase_complete=true): Появился признак инсайта, облегчения или нового взгляда на ситуацию.""",
    
    4: """ФАЗА 4: ПРАКТИЧЕСКИЙ ЯКОРЬ.
Твоя цель: Заземлить инсайт в материю.
ТАКТИКА: Сформулируй короткую поддерживающую фразу («Код Силы») и попроси выбрать одно физическое микро-действие на сегодня.
ОБЯЗАТЕЛЬНО: Оцени уровень вибраций пользователя по Шкале Хокинса (hawkins_score_estimation) от 20 до 1000.
УСЛОВИЕ ПЕРЕХОДА (phase_complete=true): Пользователь принял установку или назвал конкретное действие."""
}

async def reflection_chat_message(
    chat_history: list[dict],
    user_message: str,
    sphere: str = "IDENTITY",
    current_phase: int = 1,
    gender: str = "не указан"
) -> tuple[str, bool, dict]:
    """
    Generate structured AI response for an interactive 4-phase reflection session.
    Returns (ai_response_text, is_phase_complete, analysis_dict)
    """
    sphere_style = SPHERE_AGENT_STYLES.get(sphere, "мудрый проводник")
    phase_instructions = PHASE_PROMPTS.get(current_phase, PHASE_PROMPTS[1])
    
    system_prompt = f"""Ты — ИИ-психолог AVATAR, обладающий огромным опытом и глубокой эмпатией. 
Твой стиль: {sphere_style}. Ты говоришь как живой человек, а не как алгоритм.
Пол пользователя: {chat_history[0].get('gender') if chat_history and isinstance(chat_history[0], dict) else 'не указан'} (используй корректные окончания и стиль обращения).
Язык: RU. Всегда пиши только на русском.

{phase_instructions}

ЖЕСТКИЕ ПРАВИЛА ОБЩЕНИЯ:
1. НИКАКИХ КЛИШЕ: Запрещены фразы «Я понимаю...», «Вы упомянули...», «Похоже, что...», «Это звучит как...».
2. НЕТ ПОВТОРЕНИЯМ: Не повторяй слова пользователя дословно. Используй синонимы, живые метафоры и психологические образы.
3. ГИПОТЕЗА ВМЕСТО ВОПРОСА: Вместо того чтобы просто спрашивать, предлагай мягкие прозрения. «Я чувствую в твоих словах не столько гнев, сколько глубокую усталость от необходимости быть сильным. Это откликается внутри?»
4. ЛАКОНИЧНОСТЬ: Ответ строго 2-3 предложения. Один глубокий вопрос или предложение в конце.
5. ПРОГРЕСС ИЛИ СМЕНА: Если пользователь застрял или пишет кратко, НЕ ПОВТОРЯЙ вопрос. Смени тактику, зайди через тело или предложи свою интерпретацию. 
6. ОТВЕТ ТОЛЬКО В JSON.
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-10:])
    
    if user_message.strip():
        messages.append({"role": "user", "content": user_message})

    # Call LLM with Structured Outputs
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_FAST,
            messages=messages,
            temperature=0.7,
            response_format={
                "type": "json_schema", 
                "json_schema": {"name": "reflection_schema", "schema": ReflectionResponse.model_json_schema()}
            }
        )
        
        # Parse output
        raw_content = response.choices[0].message.content
        result_data = ReflectionResponse.model_validate_json(raw_content)
        
        analysis_dict = {
            "extracted_emotion": result_data.extracted_emotion,
            "hawkins_score": result_data.hawkins_score_estimation
        }
        
        return result_data.ai_response, result_data.phase_complete, analysis_dict
    except Exception as e:
        # Fallback in case of API or parsing error
        print(f"[Reflection Error] AI agent failure: {e}")
        return "Я рядом. Давай попробуем просто подышать и почувствовать: на что сейчас в твоем внутреннем пространстве больше всего хочется направить внимание?", False, {"extracted_emotion": "Unknown", "hawkins_score": 200}
