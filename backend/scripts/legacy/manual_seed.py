import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL")

async def seed():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # Create table if not exists (minimal schema)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS visual_stimuli (
                id SERIAL PRIMARY KEY,
                image_url VARCHAR(512) NOT NULL,
                archetype_category VARCHAR(64) NOT NULL,
                tags JSONB DEFAULT '[]',
                diagnostic_value_score FLOAT DEFAULT 1.0,
                selection_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                avg_reaction_time_ms FLOAT DEFAULT 0.0,
                generation_params JSONB DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS visual_diagnostic_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                shown_stimuli_ids JSONB NOT NULL,
                selected_stimulus_id INTEGER,
                reaction_time_ms INTEGER,
                context_tag VARCHAR(64),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_behavioral_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                preferred_archetypes JSONB DEFAULT '{}',
                decision_speed_rating FLOAT DEFAULT 0.5,
                seen_stimuli_history JSONB DEFAULT '[]',
                behavioral_pattern_summary TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Insert initial stimuli
        stimuli = [
            ("https://images.unsplash.com/photo-1500964757637-c85e8a162699?q=80&w=500", "path", '["mountain", "road", "freedom"]'),
            ("https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?q=80&w=500", "path", '["forest", "fog", "mystery"]'),
            ("https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?q=80&w=500", "conflict", '["storm", "lightning", "power"]'),
            ("https://images.unsplash.com/photo-1533134486753-c833f0ed4866?q=80&w=500", "conflict", '["lava", "fire", "destruction"]'),
            ("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=500", "peace", '["beach", "ocean", "calm"]'),
            ("https://images.unsplash.com/photo-1499346030926-9a72daac6c63?q=80&w=500", "peace", '["clouds", "sunset", "soft"]'),
            ("https://images.unsplash.com/photo-1516912481808-3b043c1dc83d?q=80&w=500", "isolation", '["arctic", "ice", "loneliness"]'),
            ("https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?q=80&w=500", "isolation", '["desert", "dune", "vastness"]'),
            ("https://images.unsplash.com/photo-1501004318641-729e8c3986e7?q=80&w=500", "growth", '["sprout", "nature", "life"]'),
            ("https://images.unsplash.com/photo-1466692473998-1620a52f63a1?q=80&w=500", "growth", '["garden", "blooming", "abundance"]'),
            ("https://images.unsplash.com/photo-1534447677768-be436bb09401?q=80&w=500", "unknown", '["space", "nebula", "infinite"]'),
            ("https://images.unsplash.com/photo-1502134249126-9f3755a50d78?q=80&w=500", "unknown", '["blackhole", "void", "deep"]'),
        ]

        for url, cat, tags in stimuli:
            await conn.execute(text(
                "INSERT INTO visual_stimuli (image_url, archetype_category, tags) VALUES (:url, :cat, :tags)"
            ), {"url": url, "cat": cat, "tags": tags})
            
        print("Successfully seeded visual stimuli.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
