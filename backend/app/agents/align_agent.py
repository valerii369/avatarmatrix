from typing import Optional
from pydantic import BaseModel, Field
from app.agents.common import (
    client, settings, ARCHETYPES, SPHERES, MATRIX_DATA,
    SPHERE_AGENT_STYLES, LEVEL_METHODOLOGIES, LEVEL_GOALS
)
from app.agents.hawkins_agent import get_hawkins_agent_level

class AlignmentResponse(BaseModel):
    ai_response: str = Field(description="Ответ пользователю согласно текущему протоколу (2-4 предложения).")
    is_depth_sufficient: bool = Field(description="True, если пользователь показал проработку на уровне чувств/тела. False, если ответ формальный, 'от ума' (байпасинг), или слишком короткий.")
    hawkins_score_estimation: int = Field(description="Оценка текущего состояния по шкале Хокинса (от 20 до 1000) на основе последней реплики.")
    final_insight: Optional[str] = Field(default=None, description="ТОЛЬКО ДЛЯ 3-Й СТАДИИ ПРИ ЗАВЕРШЕНИИ: Главный инсайт сессии.")
    integration_plan: Optional[str] = Field(default=None, description="ТОЛЬКО ДЛЯ 3-Й СТАДИИ ПРИ ЗАВЕРШЕНИИ: 1 конкретное микро-действие на неделю.")

async def alignment_session_message(
    stage: int,
    archetype_id: int,
    sphere: str,
    hawkins_score: int,
    chat_history: list[dict],
    user_message: str,
    core_belief: str = "",
    shadow_pattern: str = "",
    history_context: str = "",
    is_deepening: bool = False
) -> dict:
    """Generate AI response for an alignment session stage using Structured JSON Outputs."""
    archetype = ARCHETYPES.get(archetype_id, {})
    sphere_data = SPHERES.get(sphere, {})
    agent_level = get_hawkins_agent_level(hawkins_score)
    methodology = LEVEL_METHODOLOGIES.get(agent_level, LEVEL_METHODOLOGIES.get(1))
    sphere_style = SPHERE_AGENT_STYLES.get(sphere, "мудрый проводник")
    
    # Identify overarching goal based on Hawkins range
    goal_key = "SURVIVAL"
    if 200 <= hawkins_score < 500: goal_key = "GROWTH"
    elif hawkins_score >= 500: goal_key = "PRESENCE"
    current_goal = LEVEL_GOALS[goal_key]["goal"]

    # Sphere specific data
    techniques = ", ".join(sphere_data.get("techniques", []))
    patterns = ", ".join(sphere_data.get("patterns", []))
    
    # Archetype components from Matrix (Sphere-Specific)
    matrix = MATRIX_DATA.get(str(archetype_id), {}).get(sphere, {})
    
    # Prioritize Matrix data, fallback to general Archetype data
    arch_name = archetype.get('name', 'Архетип')
    arch_light = matrix.get("light", archetype.get('light', ''))
    arch_description = matrix.get("description", archetype.get('description', ''))
    arch_shadow = matrix.get("shadow", archetype.get('shadow', ''))
    
    # For reference
    arch_base_shadow = archetype.get('shadow', '')
    arch_base_light = archetype.get('light', '')

    protocols = {
        1: f"ПРОТОКОЛ 1: РЕГУЛЯЦИЯ (СОМАТИКА И ТЕНЬ). Задача: обнаружить напряжение в теле, связанное с паттерном, и осознать его защитную функцию (вторичную выгоду). Теневой аспект: {arch_shadow}. Техники сферы: {techniques}.",
        2: f"ПРОТОКОЛ 2: ИНТЕГРАЦИЯ РЕСУРСА (СВЕТ). Задача: впустить Свет Архетипа ({arch_name}: {arch_light}) в место напряжения. Прожить новое состояние расширения и тепла в теле через 'Архетипическое Дыхание'.",
        3: f"ПРОТОКОЛ 3: ОБНОВЛЕНИЕ СЦЕНАРИЯ (ДЕЙСТВИЕ). Задача: сформировать новую поведенческую формулу (Код Силы). Представить конкретную ситуацию из жизни, где ты действуешь по-новому. Итог: ОДНО МИКРО-ДЕЙСТВИЕ на неделю.",
    }

    deepening_prompt = ""
    if is_deepening:
        deepening_prompt = "\nВНИМАНИЕ: Ответ пользователя был поверхностным. НЕ переходи к следующему протоколу. Углуби текущий процесс, требуй больше соматических (телесных) деталей.\n"

    system_prompt = f""" Ты — агент ВЫРАВНИВАНИЯ системы AVATAR. Стиль: {sphere_style}.
Архетип: {arch_name} | Сфера: {sphere_data.get('name_ru', sphere)}
Уровень Хокинса: {hawkins_score} | Методология: {methodology['style']}

ГЛОБАЛЬНАЯ ЦЕЛЬ: {current_goal}

ИНСТРУКЦИЯ (СТРОГО):
- Ты ведешь пользователя через 3 протокола развития.
- ТЕКУЩИЙ ПРОТОКОЛ {stage}/3: {protocols.get(stage, protocols[1])}
{deepening_prompt}

ПРАВИЛА МАСТЕРСТВА:
1. СОМАТИЧЕСКИЙ ЯКОРЬ: В каждом ответе возвращай внимание пользователя к ощущениям в теле.
2. БЕЗ ПСИХОАНАЛИЗА: Не объясняй 'почему', помогай 'прожить'.
3. СВЕТ И ТЕНЬ: Используй данные матрицы для этой сферы: Тень — {arch_shadow}, Свет — {arch_light}.
4. КОРОТКО: Ответ 2-4 предложения. 
5. ОДИН ВОПРОС: Всегда заканчивай одним открытым вопросом.
6. ФИНАЛ: В 3-м протоколе обязательно доведи до конкретного микро-действия в реальности.
6. МЕТРИКИ ОЦЕНКИ (JSON поля):
   - **is_depth_sufficient**: Оцени ИСКРЕННОСТЬ. Если юзер пишет от головы ("я все понял") без включения чувств и тела — ставь false.
   - **hawkins_score_estimation**: Замерь вибрацию. Скачок больше чем на 150 пунктов за раз невозможен без катарсиса.
   - **final_insight / integration_plan**: Заполни только если это 3-й протокол и юзер дал готовность ДЕЙСТВОВАТЬ. Иначе null.
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-15:])
    if user_message.strip():
        messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_FAST, # Идеально для частых JSON-ответов
            messages=messages,
            response_format={
                "type": "json_schema", 
                "json_schema": {"name": "alignment_schema", "schema": AlignmentResponse.model_json_schema()}
            }
        )
        
        result_data = AlignmentResponse.model_validate_json(response.choices[0].message.content)
        return result_data.model_dump()
        
    except Exception as e:
        print(f"[Alignment Error] {e}")
        return {
            "ai_response": "Дыши. Что ты чувствуешь прямо сейчас?",
            "is_depth_sufficient": False,
            "hawkins_score_estimation": hawkins_score,
            "final_insight": None,
            "integration_plan": None
        }


