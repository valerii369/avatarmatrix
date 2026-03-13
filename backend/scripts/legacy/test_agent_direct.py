"""Direct test of the onboarding agent without HTTP overhead."""
import asyncio
import traceback
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User
from app.agents.onboarding_agent import extract_onboarding_cards

async def run_test():
    # Get valid user
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No users found!")
            return
        user_id = user.id
        print(f"User ID: {user_id}")
    
    chat_history = [
        {"role": "user", "content": "Привет! Я готов к диагностике."},
        {"role": "assistant", "content": "Что для тебя сейчас важнее всего?"},
        {"role": "user", "content": "Хочу найти своё предназначение, мне важна самореализация."},
        {"role": "assistant", "content": "А как насчет отношений?"},
        {"role": "user", "content": "Хочу глубоких, осознанных отношений, но сначала понять себя."},
        {"role": "assistant", "content": "Понял. Что тебя останавливает?"},
        {"role": "user", "content": "Страх не соответствовать ожиданиям. Я хорошо чувствую людей."},
    ]
    
    try:
        print("\n--- Running extract_onboarding_cards ---")
        cards = await extract_onboarding_cards(chat_history)
        print(f"\nExtracted {len(cards)} cards:")
        for c in cards:
            print(f"  archetype_id={c['archetype_id']}, sphere={c['sphere']}, score={c['score']}")
            print(f"    reason: {c['reason']}")
    except Exception:
        print(f"\nERROR in extract_onboarding_cards:\n{traceback.format_exc()}")
        return
    
    # Now test the DB write
    try:
        print("\n--- Testing DB write ---")
        from app.models import CardProgress
        from app.models.card_progress import CardStatus
        async with AsyncSessionLocal() as db:
            rec_lookup = {(c["archetype_id"], c["sphere"]): c["score"] for c in cards}
            
            existing_result = await db.execute(select(CardProgress).where(CardProgress.user_id == user_id))
            existing_cards = {(cp.archetype_id, cp.sphere): cp for cp in existing_result.scalars().all()}
            
            written = 0
            for (arch_id, sphere), score in rec_lookup.items():
                key = (arch_id, sphere)
                if key in existing_cards:
                    cp = existing_cards[key]
                    cp.is_recommended_ai = True
                    cp.ai_score = score
                    if cp.status == CardStatus.LOCKED:
                        cp.status = CardStatus.RECOMMENDED
                    db.add(cp)
                else:
                    cp = CardProgress(
                        user_id=user_id,
                        archetype_id=arch_id,
                        sphere=sphere,
                        status=CardStatus.RECOMMENDED,
                        is_recommended_ai=True,
                        ai_score=score,
                    )
                    db.add(cp)
                written += 1
            
            await db.commit()
            print(f"Written {written} card recommendations to DB!")
    except Exception:
        print(f"\nERROR in DB write:\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run_test())
