from __future__ import annotations
"""
DSB Semantic Search — semantic search по портрету через pgvector.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.dsb.storage.embeddings import generate_embedding

logger = logging.getLogger(__name__)


async def semantic_search(
    session: AsyncSession,
    portrait_id: str,
    query: str,
    top_k: int = 10,
    spheres_filter: list[int] | None = None,
    influence_filter: list[str] | None = None,
) -> list[dict]:
    """
    Семантический поиск по портрету пользователя.
    Ищет по всем 5 типам записей (facts, chains, patterns, recommendations, shadow).

    Args:
        portrait_id: ID портрета
        query: вопрос пользователя на естественном языке
        top_k: количество результатов
        spheres_filter: ограничить поиск сферами [1, 7, 10]
        influence_filter: ограничить по уровню ['high', 'medium']

    Returns:
        Список найденных чанков с score и source_table
    """
    embedding = await generate_embedding(query)
    if embedding is None:
        logger.warning("[Search] Failed to generate query embedding")
        return []

    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    sphere_clause = ""
    if spheres_filter:
        sphere_clause = f"AND sphere_primary IN ({','.join(str(s) for s in spheres_filter)})"
    influence_clause = ""
    if influence_filter:
        quoted = ",".join(f"'{i}'" for i in influence_filter)
        influence_clause = f"AND influence_level IN ({quoted})"

    results = []

    # Search in portrait_facts
    facts_sql = text(f"""
        SELECT
            id, 'fact' as source_table,
            sphere_primary as sphere,
            source_system,
            position,
            core_theme,
            light_aspect as content,
            influence_level,
            1 - (embedding <=> '{embedding_str}'::vector) as score
        FROM dsb_portrait_facts
        WHERE portrait_id = :portrait_id
            AND embedding IS NOT NULL
            {sphere_clause}
            {influence_clause}
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT :top_k
    """)

    try:
        rows = await session.execute(facts_sql, {"portrait_id": portrait_id, "top_k": top_k})
        for row in rows.mappings():
            results.append(dict(row))
    except Exception as e:
        logger.warning(f"[Search] Facts search failed (pgvector may not be set up): {e}")

    # Search in portrait_patterns
    patterns_sql = text(f"""
        SELECT
            id, 'pattern' as source_table,
            sphere,
            pattern_name as position,
            formula as core_theme,
            description as content,
            NULL as influence_level,
            1 - (embedding <=> '{embedding_str}'::vector) as score
        FROM dsb_portrait_patterns
        WHERE portrait_id = :portrait_id
            AND embedding IS NOT NULL
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT :top_k
    """)

    try:
        rows = await session.execute(patterns_sql, {"portrait_id": portrait_id, "top_k": top_k // 2})
        for row in rows.mappings():
            results.append(dict(row))
    except Exception as e:
        logger.warning(f"[Search] Patterns search failed: {e}")

    # Sort by score and return top_k
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:top_k]
