"""
Fixed AI Onboarding Agent:
1. Summarizes the diagnostic conversation
2. Gets embedding for the user summary
3. Vector searches avatar_cards (returns archetype_id 0-21 + sphere)  
4. Uses LLM to score and rank TOP results
5. Returns correct {archetype_id, sphere, score, reason} dicts
"""
import json
import os
from openai import AsyncOpenAI
from sqlalchemy.future import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.avatar_card import AvatarCard

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "archetypes.json")) as f:
    ARCHETYPES = json.load(f)
    
with open(os.path.join(DATA_DIR, "spheres.json")) as f:
    SPHERES_DATA = json.load(f)

ARCHETYPE_NAMES = {a["id"]: a["name"] for a in ARCHETYPES}
SPHERE_NAMES = {s["key"]: s["name_ru"] for s in SPHERES_DATA}


from pydantic import BaseModel, Field

class OnboardingResponse(BaseModel):
    ai_response: str = Field(description="Текст ответа для пользователя.")
    is_ready: bool = Field(description="Установи в true, если собрано достаточно данных о болях и целях пользователя, и пора завершать диагностику.")

async def generate_onboarding_response(chat_history: list[dict], gender: str = None) -> tuple[str, bool]:
    """
    Generate the next AI response in the onboarding diagnostic flow using JSON Structured Outputs.
    chat_history should include previous user/assistant messages.
    Returns (response_text, is_ready)
    """
    # Fast-Fail Logic: If it's the very first user message and it's too short/uninformative.
    if len(chat_history) == 1 and chat_history[0]["role"] == "user":
        user_msg = chat_history[0].get("content", "").strip()
        if len(user_msg) < 15 and user_msg.lower() not in ["поехать", "начать", "поехали"]:
            return "Пожалуйста, расскажите чуть подробнее. Чем больше контекста вы дадите сейчас, тем точнее система подберет ваши Архетипические Карты. Что именно вас сейчас беспокоит?", False

    gender_context = f"Учитывай, что пол пользователя: {gender}." if gender else ""
    
    system_prompt = f"""Ты — ИИ-диагност системы AVATAR.
Твоя цель — провести интенсивное, глубокое интервью с пользователем (максимум 3 вопроса), чтобы точно понять его текущую жизненную ситуацию, боли, стремления и точки роста.
Ты используешь методологию '3 Зеркала' (на базе Окна Джохари):
1. **Зеркало Фактов**: Выявление явной боли (Что болит в реальности? Отношения, деньги, выгорание?)
2. **Зеркало Тени (Скрытая выгода)**: Почему эта боль до сих пор не решена? В чем скрытый профит текущего состояния?
3. **Зеркало Потенциала**: Как выглядит идеальный исход?

{gender_context}
ОБЯЗАТЕЛЬНО отвечай на русском языке. Используй обращения, соответствующие полу пользователя, если он указан.

ПРАВИЛА ДИАЛОГА:
- Задавай только глубокие, сдвоенные вопросы (сразу в суть).
- Не веди светских бесед. Твоя роль — сканер души.
- Анализируй ГЛУБИНУ и ПОЛНОТУ ответов. Если пользователь уже на 1-м или 2-м вопросе дал исчерпывающий ответ, НЕ затягивай диалог.
- Отвечай ИСКЛЮЧИТЕЛЬНО в формате JSON!

ТРЕБОВАНИЯ К ЗАВЕРШЕНИЮ (is_ready=true):
- Как только собраны данные о болях, затыках и целях (обычно после 2-3 реплик юзера), установи 'is_ready: true'.
- В поле 'ai_response' напиши завершающую фразу. Например: 'Благодарю за откровенность. Я вижу ваши ключевые узлы напряжения и точки роста. Первичный слепок готов. Запускаю протокол синхронизации.'
- КАТЕГОРИЧЕСКИ ЗАПРЕЩАЕТСЯ называть или угадывать конкретные архетипы, система сделает это сама.
"""
    
    messages = [{"role": "system", "content": system_prompt}] + chat_history

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_FAST, # gpt-4o-mini
            messages=messages,
            temperature=0.6,
            response_format={
                "type": "json_schema", 
                "json_schema": {"name": "onboarding_schema", "schema": OnboardingResponse.model_json_schema()}
            }
        )
        result_data = OnboardingResponse.model_validate_json(response.choices[0].message.content)
        return result_data.ai_response, result_data.is_ready
    except Exception as e:
        print(f"[Onboarding Agent Error] {e}")
        return "Я анализирую ваши слова. Пожалуйста, расскажите еще немного о том, к какому состоянию вы хотите прийти.", False


async def extract_onboarding_cards(chat_history: list[dict]) -> list[dict]:
    """
    Analyze the full chat history, perform vector search, and evaluate cards.
    
    CRITICAL: Returns list of dicts with archetype_id (0-21) and sphere (string key).
    These values come directly from AvatarCard records in the vector DB.
    """
    history_text = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in chat_history])
    
    # 1. Summarize user psychological state into a single paragraph
    summary_prompt = f"""На основе этого диалога диагностики напиши краткую выжимку (1-2 абзаца) психологического портрета пользователя:
- Его текущие боли, страхи, внутренние конфликты
- Его ключевые желания, стремления, ценности
- Активные жизненные сферы (отношения, самореализация, деньги, духовность и т.д.)
- Доминирующие архетипические паттерны (тень/свет)

ДИАЛОГ:
{history_text[:4000]}

Пиши от 3-го лица. Фокус на внутренних состояниях, не на внешних событиях. Эта выжимка будет использована для семантического поиска по архетипам."""

    try:
        summary_resp = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=400,
            temperature=0.3,
        )
        user_summary = summary_resp.choices[0].message.content
    except Exception as e:
        print(f"[Onboarding Summary Error] {e}")
        user_summary = "Пользователь проходит диагностику для определения своих архетипических паттернов и целей."

    # 2. Get embedding for the summary
    try:
        emb_resp = await client.embeddings.create(
            input=user_summary,
            model="text-embedding-3-small"
        )
        user_embedding = emb_resp.data[0].embedding
    except Exception as e:
        print(f"[Onboarding Embedding Error] {e}")
        user_embedding = [0.0] * 1536

    # 3. Vector search — returns AvatarCard objects with correct archetype_id (0-21) and sphere
    top_cards = []
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AvatarCard)
            .order_by(AvatarCard.embedding.cosine_distance(user_embedding))
            .limit(15)  # get top 15 for LLM to choose from
        )
        result = await session.execute(stmt)
        top_cards = result.scalars().all()

    if not top_cards:
        return []

    # 4. Build context for LLM ranking — use CORRECT archetype_id from the record
    context_cards = []
    for c in top_cards:
        arch_name = ARCHETYPE_NAMES.get(c.archetype_id, f"Архетип {c.archetype_id}")
        sphere_name = SPHERE_NAMES.get(c.sphere, c.sphere)
        context_cards.append({
            "archetype_id": c.archetype_id,  # ← correct 0-21 value
            "sphere": c.sphere,               # ← correct sphere key
            "arch_name": arch_name,
            "sphere_name": sphere_name,
            "shadow_preview": c.shadow[:200] if c.shadow else "",
            "light_preview": c.light[:200] if c.light else "",
        })

    # Build a numbered list for the LLM
    numbered_list = "\n".join([
        f"{i+1}. archetype_id={c['archetype_id']} ({c['arch_name']}) | sphere={c['sphere']} ({c['sphere_name']})\n"
        f"   Тень: {c['shadow_preview']}...\n"
        f"   Свет: {c['light_preview']}..."
        for i, c in enumerate(context_cards)
    ])

    prompt = f"""Ты — аналитик системы AVATAR.
Ниже — психологический портрет пользователя и ТОП-15 архетипических карт из векторной базы, семантически близких к его ситуации.

ПОРТРЕТ ПОЛЬЗОВАТЕЛЯ:
{user_summary}

ТОП-15 КАРТ (пронумерованы от 1 до {len(context_cards)}):
{numbered_list}

ЗАДАЧА:
1. Выбери ровно от 3 до 5 карт, которые НАИБОЛЕЕ ТОЧНО отражают ситуацию пользователя. (Минимум 3, максимум 5).
2. Для каждой выбранной карты дай score от 0.6 до 1.0 (1.0 = идеальное совпадение).
3. Напиши 1 предложение (reason) на русском — почему именно эта карта подходит.

ВАЖНО: В ответе используй ТОЧНЫЕ значения archetype_id (от 0 до 21) и sphere из предложенного списка. Выбирай только те карты, которые реально присутствуют в ТОП-15!

Отвечай СТРОГО в формате JSON без каких-либо оберток markdown, только голый JSON:
{{
  "cards": [
    {{
      "archetype_id": <число 0-21 из списка>,
      "sphere": "<КЛЮЧ_СФЕРЫ из списка>",
      "score": <0.6-1.0>,
      "reason": "<1 предложение почему>"
    }}
  ]
}}"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content
    except Exception as e:
        print(f"[Onboarding Card Ranking Error] {e}")
        # Return top 5 from vector search directly if LLM fails
        return [
            {
                "archetype_id": c["archetype_id"],
                "sphere": c["sphere"],
                "score": 0.7,
                "reason": "Прямое семантическое совпадение с запросом.",
            }
            for c in context_cards[:5]
        ]
        # Remove any markdown code block wrappers if they slip through
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[-1]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
        
        data = json.loads(raw_content)
        cards = data.get("cards", [])
        
        # Validate that returned archetype_ids and spheres exist in context
        valid_combos = {(c["archetype_id"], c["sphere"]) for c in context_cards}
        validated = []
        for card in cards:
            arch_id = card.get("archetype_id")
            sphere = card.get("sphere", "").upper()
            if (arch_id, sphere) in valid_combos:
                validated.append({
                    "archetype_id": arch_id,
                    "sphere": sphere,
                    "score": float(card.get("score", 0.7)),
                    "reason": card.get("reason", ""),
                })
        
        # Guarantee we return at least 3 cards if possible
        if len(validated) < 3:
            used_combos = {(v["archetype_id"], v["sphere"]) for v in validated}
            for c in context_cards:
                if len(validated) >= 3:
                    break
                combo = (c["archetype_id"], c["sphere"])
                if combo not in used_combos:
                    validated.append({
                        "archetype_id": c["archetype_id"],
                        "sphere": c["sphere"],
                        "score": 0.7,
                        "reason": "Семантическое совпадение с портретом пользователя по векторной базе.",
                    })
                    used_combos.add(combo)
        
        return validated
        
    except Exception as e:
        import logging
        logging.error(f"Error parsing LLM card extraction, falling back to vector search: {e}")
        # Fallback: use top-5 from vector search directly to ensure cards activate
        return [
            {
                "archetype_id": c["archetype_id"],
                "sphere": c["sphere"],
                "score": 0.7,
                "reason": "Прямое семантическое совпадение с запросом.",
            }
            for c in context_cards[:5]
        ]
