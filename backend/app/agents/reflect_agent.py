from .common import client, settings, SPHERE_AGENT_STYLES

async def reflection_chat_message(
    chat_history: list[dict],
    user_message: str,
    sphere: str = "IDENTITY"
) -> tuple[str, bool]:
    """
    Generate AI response for an interactive reflection session.
    Goal: Understand situation, reactions, and shift state to positive.
    Returns (response_text, is_ready_to_finish)
    """
    sphere_style = SPHERE_AGENT_STYLES.get(sphere, "мудрый проводник")
    
    system_prompt = f"""Ты — ИИ-проводник в системе AVATAR, специализирующийся на глубокой рефлексии.
Твоя роль: {sphere_style}.

Твои задачи в диалоге:
1. Внимательно выслушать пользователя и уточнить детали ситуации (Что произошло? Какие факты?).
2. Помочь пользователю осознать его реакции (Какие эмоции возникли? Какие мысли в голове? Какие ощущения в теле?).
3. Трансформировать состояние: мягко привести пользователя к осознанности, принятию или ресурсному состоянию.

ПРАВИЛА:
- Не давай готовых советов сразу. Задавай вопросы, которые заставляют задуматься.
- Будь эмпатичным, но сохраняй позицию наблюдателя.
- Ответы должны быть лаконичными (2-4 предложения).
- Всегда заканчивай ОДНИМ открытым вопросом.
- Если ты чувствуешь, что состояние пользователя «выровнялось», он осознал урок или ситуация разобрана конструктивно, добавь в самый конец своего сообщения скрытый тег [READY].
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-10:])
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_FAST,
        messages=messages,
        temperature=0.8,
    )
    
    content = response.choices[0].message.content or "..."
    is_ready = "[READY]" in content
    clean_content = content.replace("[READY]", "").strip()
    
    return clean_content, is_ready
