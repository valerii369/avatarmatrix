import sys
import os
import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import uuid
import tiktoken
from dotenv import load_dotenv
load_dotenv("/Users/valeriiguro/Desktop/AVATARv1.0/backend/.env")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.dsb.storage.embeddings import generate_embeddings_batch

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
BOOKS_DIR = os.path.join(DATA_DIR, "books_western_astrology")
QDRANT_PATH = os.path.join(DATA_DIR, "qdrant_storage")

async def ingest():
    if not os.path.exists(QDRANT_PATH):
        os.makedirs(QDRANT_PATH)
        
    client = AsyncQdrantClient(path=QDRANT_PATH)
    collection_name = "books_western_astrology"
    
    # Check if collection exists
    if not await client.collection_exists(collection_name):
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        print(f"Created collection {collection_name}")
        
    documents = []
    
    if os.path.exists(BOOKS_DIR):
        for filename in os.listdir(BOOKS_DIR):
            if not filename.endswith(".md"):
                continue
                
            with open(os.path.join(BOOKS_DIR, filename), "r") as f:
                content = f.read()
                
            lines = content.split("\n")
            title = filename.replace("_", " ").replace(".md", "")
            author = "Unknown"
            topic = "General"
            
            current_chunk = []
            
            for line in lines:
                if line.startswith("# "):
                    title = line[2:].strip()
                elif line.startswith("## Author:"):
                    author = line[10:].strip()
                elif line.startswith("### Section:"):
                    if current_chunk:
                        text = "\n".join(current_chunk).strip()
                        if len(text) > 10:
                            documents.append({
                                "text": text,
                                "metadata": {
                                    "book_title": title,
                                    "author": author,
                                    "chapter": topic,
                                    "topic": topic
                                }
                            })
                    topic = line[12:].strip()
                    current_chunk = [line]
                else:
                    current_chunk.append(line)
                    
            if current_chunk:
                text = "\n".join(current_chunk).strip()
                if len(text) > 10:
                    documents.append({
                        "text": text,
                        "metadata": {
                            "book_title": title,
                            "author": author,
                            "chapter": topic,
                            "topic": topic
                        }
                    })
                    
    print(f"Found {len(documents)} chunks to ingest.")
    
    if not documents:
        return
        
    # Generate embeddings
    texts_to_embed = [d["text"] for d in documents]
    embeddings = await generate_embeddings_batch(texts_to_embed)
    
    points = []
    for doc, emb in zip(documents, embeddings):
        if emb:
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload=doc["metadata"] | {"text": doc["text"]}
            ))
            
    if points:
        await client.upsert(
            collection_name=collection_name,
            points=points
        )
        print(f"Successfully ingested {len(points)} chunks into {collection_name}.")
        
    await client.close()
        
if __name__ == "__main__":
    asyncio.run(ingest())
