import asyncio
import traceback
from datetime import datetime
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User, NatalChart, CardProgress
from app.core.astrology.natal_chart import calculate_natal_chart, geocode_place, to_dict as chart_to_dict
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
from app.core.astrology.llm_engine import synthesize_sphere_descriptions
from app.core.astrology.vector_matcher import match_archetypes_to_spheres

async def test_astro_calc():
    user_id = 4 # Use user 4 which we checked before
    birth_date_str = "1990-01-15"
    birth_time = "14:30"
    birth_place = "Moscow, Russia"
    
    print(f"--- Starting Astro Calc for User {user_id} ---")
    
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        if not user:
            print("User not found")
            return

        try:
            print("1. Geocoding...")
            lat, lon, tz_name = await geocode_place(birth_place)
            print(f"   Result: {lat}, {lon}, {tz_name}")
            
            print("2. Calculating Natal Chart...")
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
            chart = calculate_natal_chart(birth_date, birth_time, lat, lon, tz_name)
            chart_dict = chart_to_dict(chart)
            print("   Chart calculated successfully.")
            
            print("3. Calculating Aspects...")
            aspects = calculate_aspects(chart_dict["planets"])
            aspects_dict = aspects_to_dict(aspects)
            print(f"   Found {len(aspects)} aspects.")
            
            print("4. Synthesizing Sphere Descriptions via LLM...")
            sphere_descriptions = await synthesize_sphere_descriptions(chart_dict, aspects_dict)
            print(f"   Descriptions: {list(sphere_descriptions.keys())}")
            
            print("5. Matching Archetypes to Spheres (Vector Search)...")
            recommended_astro = await match_archetypes_to_spheres(db, sphere_descriptions)
            print(f"   Recommended {len(recommended_astro)} cards.")
            
            for r in recommended_astro:
                print(f"   - {r.sphere}: {r.archetype_id} (priority: {r.priority})")

            print("6. DB Writes (Simulated)...")
            # We won't actually commit here, just check if it works
            # ... skipping the loop for brevity, just seeing if we get here
            
            print("--- SUCCESS ---")
            
        except Exception as e:
            print(f"\n!!! ERROR !!!\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_astro_calc())
