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


async def generate_onboarding_response(chat_history: list[dict]) -> str:
    """
    Generate the next AI response in the onboarding diagnostic flow.
    chat_history should include previous user/assistant messages.
    """
    system_prompt = """Ты — ИИ-диагност системы AVATAR.
Твоя цель — провести короткое (3-5 шагов) глубокое интервью с пользователем, чтобы понять его текущую жизненную ситуацию, боли, стремления и точки роста.
Ты помогаешь человеку выявить те Сферы жизни и Архетипы, которые сейчас требуют внимания или активированы.

МЕТОДОЛОГИЯ:
1. Задавай по одному глубокому, открытому вопросу за раз.
2. Не давай советов. Твоя роль — зеркало и аналитик.
3. Копай глубже: если человек отвечает поверхностно, спроси, что стоит за этим.
4. Фокусируйся на чувствах, текущих конфликтах или главных мечтах.
5. Стиль общения: эмпатичный, проницательный, в сеттинге системы AVATAR (как проводник в подсознание).

Если пользователь только начал диалог, твой первый вопрос должен быть широким, например: «С какой мыслью или состоянием ты проснулся сегодня?» или «Что сейчас в твоей жизни требует наибольшего внимания, но ты откладываешь это?».

Если диалог длится уже 4-5 обменов репликами, плавно подведи итог и скажи, что ты готов синхронизировать его карты.
"""
    
    messages = [{"role": "system", "content": system_prompt}] + chat_history

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=500,
        temperature=0.6,
    )
    
    return response.choices[0].message.content


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

    summary_resp = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=400,
        temperature=0.3,
    )
    user_summary = summary_resp.choices[0].message.content

    # 2. Get embedding for the summary
    emb_resp = await client.embeddings.create(
        input=user_summary,
        model="text-embedding-3-small"
    )
    user_embedding = emb_resp.data[0].embedding

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
1. Выбери 3-5 карт, которые НАИБОЛЕЕ ТОЧНО отражают ситуацию пользователя.
2. Для каждой карты дай score от 0.6 до 1.0 (1.0 = идеальное совпадение).
3. Напиши 1 предложение reason на русском — почему именно эта карта.

ВАЖНО: В ответе используй ТОЧНЫЕ значения archetype_id и sphere из списка выше, не придумывай новые!

Отвечай только в формате JSON:
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

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    
    try:
        data = json.loads(response.choices[0].message.content)
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
        
        # If LLM hallucinated and we have 0 valid, fall back to top-3 from vector search directly
        if not validated:
            for c in context_cards[:3]:
                validated.append({
                    "archetype_id": c["archetype_id"],
                    "sphere": c["sphere"],
                    "score": 0.7,
                    "reason": "Семантическое совпадение с портретом пользователя.",
                })
        
        return validated
        
    except Exception as e:
        # Fallback: use top-3 from vector search directly
        return [
            {
                "archetype_id": c["archetype_id"],
                "sphere": c["sphere"],
                "score": 0.7,
                "reason": "Семантическое совпадение с портретом пользователя.",
            }
            for c in context_cards[:3]
        ]
