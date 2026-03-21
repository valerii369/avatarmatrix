from __future__ import annotations
"""
DSB Embeddings — генерация векторных эмбеддингов для портрета.
Используется OpenAI text-embedding-3-small (1536 dim).
"""

import logging
from openai import AsyncOpenAI
from app.dsb.config import SPHERE_NAMES

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536


def generate_embedding_text(record: dict, record_type: str = "fact") -> str:
    """
    Формирует текст для эмбеддинга из любой записи DSB.
    Конкатенирует ключевые поля для максимальной семантической точности.
    """
    if record_type == "fact":
        sphere_name = SPHERE_NAMES.get(record.get("sphere_primary", 0), "")
        parts = [
            f"Сфера: {sphere_name}",
            f"Тема: {record.get('core_theme', '')}",
            f"Позиция: {record.get('position', '')}",
            f"Описание: {record.get('light_aspect', '')}",
            f"Тень: {record.get('shadow_aspect', '')}",
        ]
    elif record_type == "chain":
        sphere_name = SPHERE_NAMES.get(record.get("sphere", 0), "")
        parts = [
            f"Сфера: {sphere_name}",
            f"Цепочка: {record.get('chain_name', '')}",
            f"Описание: {record.get('description', '')}",
        ]
    elif record_type == "pattern":
        sphere_name = SPHERE_NAMES.get(record.get("sphere", 0), "")
        parts = [
            f"Сфера: {sphere_name}",
            f"Паттерн: {record.get('pattern_name', '')}",
            f"Формула: {record.get('formula', '')}",
            f"Описание: {record.get('description', '')}",
        ]
    elif record_type == "recommendation":
        sphere_name = SPHERE_NAMES.get(record.get("sphere", 0), "")
        parts = [
            f"Сфера: {sphere_name}",
            f"Рекомендация: {record.get('recommendation', '')}",
        ]
    elif record_type == "shadow":
        sphere_name = SPHERE_NAMES.get(record.get("sphere", 0), "")
        parts = [
            f"Сфера: {sphere_name}",
            f"Риск: {record.get('risk_name', '')}",
            f"Описание: {record.get('description', '')}",
            f"Антидот: {record.get('antidote', '')}",
        ]
    elif record_type == "meta":
        parts = [
            f"Суперпаттерн: {record.get('pattern_name', '')}",
            f"Описание: {record.get('description', '')}",
        ]
    else:
        parts = [str(record)]

    return " | ".join(p for p in parts if p.split(": ", 1)[-1].strip())


async def generate_embedding(text: str) -> list[float] | None:
    """Генерирует эмбеддинг для одного текста."""
    client = AsyncOpenAI()
    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text[:8000],  # ограничение контекста
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"[Embeddings] Failed to generate embedding: {e}")
        return None


async def generate_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Генерирует эмбеддинги для пакета текстов (до 100 за вызов)."""
    client = AsyncOpenAI()
    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[t[:8000] for t in texts],
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.error(f"[Embeddings] Batch generation failed: {e}")
        return [None] * len(texts)
