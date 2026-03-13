import asyncio
import json
import os
from sqlalchemy.future import select
from openai import AsyncOpenAI
from app.database import AsyncSessionLocal
from app.models.avatar_card import AvatarCard
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

async def get_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

async def process_card(arch_id, arch_name, sphere_key, sphere_data, sphere_map, semaphore):
    async with semaphore:
        sphere_name = sphere_map.get(sphere_key, sphere_key)
        
        # Collect all markers from levels for better vector search
        all_markers = []
        levels = sphere_data.get("levels", {})
        for lvl in levels.values():
            all_markers.extend(lvl.get("speech_markers", []))
        unique_markers = sorted(list(set(all_markers)))

        # Construct a comprehensive text representation for the vector embedding
        text_repr = f"Архетип: {arch_name}. Сфера: {sphere_name}.\n"
        text_repr += f"Общее описание: {sphere_data.get('description', '')}\n"
        text_repr += f"Тень (негативное проявление, проблемы, блоки): {sphere_data.get('shadow', '')}\n"
        text_repr += f"Свет (позитивное проявление, потенциал): {sphere_data.get('light', '')}\n"
        text_repr += f"Маркеры состояний и жалоб: {', '.join(unique_markers)}\n"

        print(f"Generating embedding for Archetype {arch_id}, Sphere {sphere_key}...")
        embedding = await get_embedding(text_repr)
        
        async with AsyncSessionLocal() as session:
            # Upsert
            stmt = select(AvatarCard).where(
                AvatarCard.archetype_id == arch_id,
                AvatarCard.sphere == sphere_key
            )
            result = await session.execute(stmt)
            card = result.scalars().first()

            if card:
                card.shadow = sphere_data.get("shadow", "")
                card.light = sphere_data.get("light", "")
                card.embedding = embedding
                card.metadata_json = sphere_data
                print(f"Updated card {arch_id} - {sphere_key}")
            else:
                new_card = AvatarCard(
                    archetype_id=arch_id,
                    sphere=sphere_key,
                    shadow=sphere_data.get("shadow", ""),
                    light=sphere_data.get("light", ""),
                    embedding=embedding,
                    metadata_json=sphere_data
                )
                session.add(new_card)
                print(f"Created card {arch_id} - {sphere_key}")
            
            await session.commit()

async def sync():
    with open(os.path.join(DATA_DIR, "archetypes.json"), encoding="utf-8") as f:
        archetypes = json.load(f)
    with open(os.path.join(DATA_DIR, "spheres.json"), encoding="utf-8") as f:
        spheres = json.load(f)
    with open(os.path.join(DATA_DIR, "archetype_sphere_matrix.json"), encoding="utf-8") as f:
        matrix = json.load(f)

    arch_map = {str(a["id"]): a["name"] for a in archetypes}
    sphere_map = {s["key"]: s["name_ru"] for s in spheres}

    semaphore = asyncio.Semaphore(10) # Process 10 cards at a time
    tasks = []

    for arch_id_str, arch_data in matrix.items():
        if arch_id_str == "_meta": continue
        arch_id = int(arch_id_str)
        arch_name = arch_map.get(arch_id_str, f"Archetype {arch_id}")

        for sphere_key, sphere_data in arch_data.items():
            if sphere_key == "_meta":
                continue
            
            tasks.append(process_card(arch_id, arch_name, sphere_key, sphere_data, sphere_map, semaphore))

    await asyncio.gather(*tasks)
    print("Sync complete!")

if __name__ == "__main__":
    asyncio.run(sync())
