import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.visual_evolution import VisualStimulus

async def seed_visual_stimuli():
    async with AsyncSessionLocal() as db:
        stimuli = [
            # PATH
            {"image_url": "https://images.unsplash.com/photo-1500964757637-c85e8a162699?q=80&w=500", "archetype_category": "path", "tags": ["mountain", "road", "freedom"]},
            {"image_url": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?q=80&w=500", "archetype_category": "path", "tags": ["forest", "fog", "mystery"]},
            
            # CONFLICT
            {"image_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?q=80&w=500", "archetype_category": "conflict", "tags": ["storm", "lightning", "power"]},
            {"image_url": "https://images.unsplash.com/photo-1533134486753-c833f0ed4866?q=80&w=500", "archetype_category": "conflict", "tags": ["lava", "fire", "destruction"]},
            
            # PEACE
            {"image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=500", "archetype_category": "peace", "tags": ["beach", "ocean", "calm"]},
            {"image_url": "https://images.unsplash.com/photo-1499346030926-9a72daac6c63?q=80&w=500", "archetype_category": "peace", "tags": ["clouds", "sunset", "soft"]},
            
            # ISOLATION
            {"image_url": "https://images.unsplash.com/photo-1516912481808-3b043c1dc83d?q=80&w=500", "archetype_category": "isolation", "tags": ["arctic", "ice", "loneliness"]},
            {"image_url": "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?q=80&w=500", "archetype_category": "isolation", "tags": ["desert", "dune", "vastness"]},
            
            # GROWTH
            {"image_url": "https://images.unsplash.com/photo-1501004318641-729e8c3986e7?q=80&w=500", "archetype_category": "growth", "tags": ["sprout", "nature", "life"]},
            {"image_url": "https://images.unsplash.com/photo-1466692473998-1620a52f63a1?q=80&w=500", "archetype_category": "growth", "tags": ["garden", "blooming", "abundance"]},
            
            # UNKNOWN
            {"image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?q=80&w=500", "archetype_category": "unknown", "tags": ["space", "nebula", "infinite"]},
            {"image_url": "https://images.unsplash.com/photo-1502134249126-9f3755a50d78?q=80&w=500", "archetype_category": "unknown", "tags": ["blackhole", "void", "deep"]},
        ]
        
        for s_data in stimuli:
            s = VisualStimulus(**s_data)
            db.add(s)
        
        await db.commit()
        print(f"Seeded {len(stimuli)} visual stimuli.")

if __name__ == "__main__":
    asyncio.run(seed_visual_stimuli())
