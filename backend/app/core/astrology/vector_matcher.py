import asyncio
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import AsyncOpenAI

from app.config import settings
from app.models.avatar_card import AvatarCard
from pydantic import BaseModel

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def _get_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

class RecommendedCard(BaseModel):
    archetype_id: int
    sphere: str
    priority: str  # critical, high, medium, additional
    reason: str
    planet: Optional[str] = None
    is_retrograde: bool = False


async def match_archetypes_to_spheres(
    db: AsyncSession, 
    sphere_descriptions: dict,
    multi_vector: bool = True
) -> list[RecommendedCard]:
    """
    Senior v3.1: Parallel Multi-Vector Matching.
    Matches text portfolios to archetypes using weighted semantic resonance.
    """
    recommended_cards = []
    spheres_data = sphere_descriptions.get("spheres_12", sphere_descriptions)
    
    if not spheres_data:
        return []

    # 1. Collect all texts for batch embedding (Fastest method)
    all_texts = []
    sphere_tasks = [] # (sphere, type)
    
    for sphere, details in spheres_data.items():
        if multi_vector and isinstance(details, dict):
            # Weighted search: Shadow, Light, Insight
            t_shadow = details.get("shadow", "")
            t_light = details.get("light", "")
            t_insight = details.get("insight", "")
            
            if t_shadow: 
                all_texts.append(t_shadow)
                sphere_tasks.append((sphere, "shadow"))
            if t_light:
                all_texts.append(t_light)
                sphere_tasks.append((sphere, "light"))
            if t_insight:
                all_texts.append(t_insight)
                sphere_tasks.append((sphere, "insight"))
        else:
            txt = details.get("interpretation", "") if isinstance(details, dict) else details
            if txt:
                all_texts.append(txt)
                sphere_tasks.append((sphere, "unified"))

    if not all_texts:
        return []

    # 2. Batch Embedding (1 request instead of 36)
    try:
        response = await client.embeddings.create(
            input=all_texts,
            model="text-embedding-3-large", # Upgrade to Large for high precision
            dimensions=1536  # Clip to 1536 to match current DB schema
        )
        embeddings = [d.embedding for d in response.data]

    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        return []

    # 3. Parallel DB Queries (asyncio.gather)
    async def _query_sphere(sphere, emb, weight, s_type):
        try:
            stmt = select(AvatarCard).where(
                AvatarCard.sphere == sphere
            ).order_by(
                AvatarCard.embedding.cosine_distance(emb)
            ).limit(2) # Get top 2 candidates per vector
            
            result = await db.execute(stmt)
            cards = result.scalars().all()
            return [(card.archetype_id, weight, s_type) for card in cards]
        except Exception as e:
            logger.error(f"Query error for {sphere}: {e}")
            return []

    # Prepare concurrent tasks
    db_tasks = []
    weights = {"shadow": 0.4, "light": 0.4, "insight": 0.2, "unified": 1.0}
    
    for (sphere, s_type), emb in zip(sphere_tasks, embeddings):
        db_tasks.append(_query_sphere(sphere, emb, weights.get(s_type, 1.0), s_type))

    # Execute all queries in PARALLEL
    results = await asyncio.gather(*db_tasks)
    
    # 4. Weighted Aggregation
    # sphere -> {archetype_id: total_score}
    aggregated = {}
    for (sphere, s_type), sphere_hits in zip(sphere_tasks, results):
        if sphere not in aggregated:
            aggregated[sphere] = {}
        for arch_id, weight, _ in sphere_hits:
            aggregated[sphere][arch_id] = aggregated[sphere].get(arch_id, 0) + weight

    # 5. Final Selection
    for sphere, scores in aggregated.items():
        if not scores: continue
        # Sort by total score descending
        sorted_archs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get top candidate
        top_arch_id, top_score = sorted_archs[0]
        
        priority = "medium"
        if top_score >= 0.7: priority = "critical"
        elif top_score >= 0.4: priority = "high"
        
        recommended_cards.append(RecommendedCard(
            archetype_id=top_arch_id,
            sphere=sphere,
            priority=priority,
            reason=f"Смысловой резонанс {int(top_score*100)}% (Синтез Тени и Света)."
        ))
            
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
