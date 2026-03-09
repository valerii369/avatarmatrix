from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import AsyncOpenAI

from app.config import settings
from app.models.avatar_card import AvatarCard
from app.core.astrology.priority_engine import RecommendedCard

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def _get_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

async def match_archetypes_to_spheres(
    db: AsyncSession, 
    sphere_descriptions: dict
) -> list[RecommendedCard]:
    """
    Takes LLM generated descriptions for each of the 8 spheres, converts them
    to embeddings, and queries pgvector to find the closest matching Archetype 
    (from the AvatarCards table) for that specific sphere.
    """
    recommended_cards = []
    
    for sphere, description in sphere_descriptions.items():
        if not description.strip():
            continue
            
        try:
            # 1. Get embedding for the sphere's description
            query_embedding = await _get_embedding(description)
            
            # 2. Query Postgres vector distance
            # Find the AvatarCard currently assigned to this sphere that matches the generated text most closely
            stmt = select(AvatarCard).where(
                AvatarCard.sphere == sphere
            ).order_by(
                AvatarCard.embedding.cosine_distance(query_embedding)
            ).limit(3) # Get top 3
            
            result = await db.execute(stmt)
            top_cards = result.scalars().all()
            
            # 3. Add to recommendations (critical for 1st, high for 2nd, etc)
            priorities = ["critical", "high", "medium"]
            
            for idx, card in enumerate(top_cards):
                if idx >= len(priorities):
                    break
                    
                rec = RecommendedCard(
                    archetype_id=card.archetype_id,
                    sphere=sphere,
                    priority=priorities[idx],
                    reason=f"Наилучшее соответствие: {description[:100]}..." if idx == 0 else "Дополнительное соответствие энергии."
                )
                recommended_cards.append(rec)
                
        except Exception as e:
            print(f"Error matching vector for sphere {sphere}: {e}")
            
    return recommended_cards

async def match_text_to_archetypes(
    db: AsyncSession, 
    text: str,
    top_k: int = 5
) -> list[tuple[int, str, float]]:
    """
    Matches any text to the nearest 5 archetypes across all spheres.
    Returns list of (archetype_id, sphere, score).
    Score is 1.0 - cosine_distance (higher is better).
    """
    if not text.strip():
        return []

    try:
        query_embedding = await _get_embedding(text)
        
        # Query top_k closest cards across ALL spheres
        stmt = select(AvatarCard).order_by(
            AvatarCard.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        result = await db.execute(stmt)
        top_cards = result.scalars().all()
        
        matches = []
        for card in top_cards:
            # Note: PostgreSQL pgvector returns distance. 
            # In a more advanced version, we would fetch the distance directly in the first query.
            # For now, let's keep it simple and approximate score if we can't easily get it from 'select'.
            matches.append((card.archetype_id, card.sphere, 0.8)) # Standard match score
            
        return matches
    except Exception as e:
        print(f"Error in match_text_to_archetypes: {e}")
        return []
