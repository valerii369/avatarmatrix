from __future__ import annotations
import os
import logging
from qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)

async def retrieve(query: str, collection: str, top_k: int = 6) -> list[dict]:
    try:
        from app.dsb.storage.embeddings import generate_embedding
        emb = await generate_embedding(query)
        if not emb:
            return []
            
        qdrant_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "qdrant_storage")
        if not os.path.exists(qdrant_path):
            return []
            
        client = AsyncQdrantClient(path=qdrant_path)
        
        if not await client.collection_exists(collection):
            await client.close()
            return []
            
        search_result = await client.search(
            collection_name=collection,
            query_vector=emb,
            limit=top_k
        )
        
        results = []
        for hit in search_result:
            results.append({
                "text": hit.payload.get("text", ""),
                "book_title": hit.payload.get("book_title", "Unknown"),
                "author": hit.payload.get("author", "Unknown"),
                "topic": hit.payload.get("topic", ""),
                "score": hit.score
            })
            
        await client.close()
        return results
    except Exception as e:
        logger.error(f"[Retriever] Error: {e}")
        return []
