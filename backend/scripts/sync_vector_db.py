import asyncio
import json
import os
import sys
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.models.avatar_card import AvatarCard
from app.agents.common import client, settings, SPHERES, ARCHETYPES

async def get_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

async def sync_vector_db():
    matrix_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "archetype_sphere_matrix.json")
    
    with open(matrix_path, "r", encoding="utf-8") as f:
        matrix = json.load(f)
    
    async with AsyncSessionLocal() as db:
        print("Starting Vector DB Sync (264 cards)...")
        
        # 0. Delete old spheres that are not in the current 12-sphere list
        current_sphere_keys = list(SPHERES.keys())
        print(f"Cleaning up old spheres not in: {current_sphere_keys}")
        await db.execute(delete(AvatarCard).where(AvatarCard.sphere.notin_(current_sphere_keys)))
        await db.commit()

        # 1. Update or insert new cards
        count = 0
        for arc_id_str, arc_spheres in matrix.items():
            if arc_id_str.startswith("_"): continue
            arc_id = int(arc_id_str)
            
            for skey, sdata in arc_spheres.items():
                if skey.startswith("_"): continue
                
                print(f"[{count+1}/264] Processing Arc {arc_id} Sphere {skey}...")
                
                # Content for embedding
                light = sdata.get("light", "")
                shadow = sdata.get("shadow", "")
                description = sdata.get("description", "")
                
                # We embed the full description which captures the essence of the archetype in this sphere
                combined_text = f"{description}\n{light}\n{shadow}"
                
                try:
                    embedding = await get_embedding(combined_text)
                    
                    # Upsert logic
                    stmt = select(AvatarCard).where(
                        AvatarCard.archetype_id == arc_id,
                        AvatarCard.sphere == skey
                    )
                    res = await db.execute(stmt)
                    existing = res.scalar_one_or_none()
                    
                    if existing:
                        existing.light = light
                        existing.shadow = shadow
                        existing.embedding = embedding
                        # Keep description in light/shadow or common if needed
                    else:
                        new_card = AvatarCard(
                            archetype_id=arc_id,
                            sphere=skey,
                            light=light,
                            shadow=shadow,
                            embedding=embedding,
                            metadata_json={"description": description}
                        )
                        db.add(new_card)
                    
                    count += 1
                    if count % 10 == 0:
                        await db.commit()
                        print(f"--- Committed {count} cards ---")
                        
                except Exception as e:
                    print(f"Error processing {arc_id} + {skey}: {e}")
                    
        await db.commit()
        print(f"Successfully synced {count} AvatarCards to Vector DB.")

if __name__ == "__main__":
    asyncio.run(sync_vector_db())
