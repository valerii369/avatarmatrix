import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User, NatalChart, CardProgress
from app.models.card_progress import CardStatus
from app.core.astrology.natal_chart import calculate_natal_chart, to_dict as chart_to_dict
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
from app.core.astrology.priority_engine import generate_recommended_cards, to_dict as cards_to_dict

SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]
ARCHETYPE_IDS = list(range(22))

async def recalculate_all():
    print("Starting mass recalculation for all users based on new astrology engine...")
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User).where(User.onboarding_done == True))).scalars().all()
        
        if not users:
            print("No onboarded users found to recalculate.")
            return

        for user in users:
            print(f"\nProcessing User ID: {user.id} ({user.first_name} {user.last_name})")
            
            try:
                # Need lat/lon/tz
                if not user.birth_lat or not user.birth_lon or not user.birth_tz:
                    print(f"Skipping user {user.id}: missing coordinates or timezone.")
                    continue

                chart = calculate_natal_chart(
                    user.birth_date, user.birth_time, user.birth_lat, user.birth_lon, user.birth_tz
                )
                chart_dict = chart_to_dict(chart)
                
                aspects = calculate_aspects(chart_dict["planets"])
                aspects_dict = aspects_to_dict(aspects)
                
                recommended_astro = generate_recommended_cards(chart)
                recommended_dict = cards_to_dict(recommended_astro)

                recommended_set = {(r.archetype_id, r.sphere): r for r in recommended_astro}

                # Update cards
                existing_cards = {
                    (cp.archetype_id, cp.sphere): cp
                    for cp in (await db.execute(select(CardProgress).where(CardProgress.user_id == user.id))).scalars().all()
                }

                for archetype_id in ARCHETYPE_IDS:
                    for sphere in SPHERES:
                        key = (archetype_id, sphere)
                        rec = recommended_set.get(key)
                        
                        if key in existing_cards:
                            cp = existing_cards[key]
                            if rec:
                                cp.is_recommended_astro = True
                                cp.astro_priority = rec.priority
                                cp.astro_reason = rec.reason
                                if cp.status == CardStatus.LOCKED:
                                    cp.status = CardStatus.RECOMMENDED
                            else:
                                cp.is_recommended_astro = False
                            db.add(cp)
                        else:
                            status = CardStatus.RECOMMENDED if rec else CardStatus.LOCKED
                            cp = CardProgress(
                                user_id=user.id,
                                archetype_id=archetype_id,
                                sphere=sphere,
                                status=status,
                                is_recommended_astro=rec is not None,
                                astro_priority=rec.priority if rec else None,
                                astro_reason=rec.reason if rec else None,
                            )
                            db.add(cp)

                # Update natal chart
                natal = (await db.execute(select(NatalChart).where(NatalChart.user_id == user.id))).scalar_one_or_none()
                if natal:
                    natal.planets_json = chart_dict
                    natal.aspects_json = aspects_dict
                    natal.recommended_cards_json = recommended_dict
                    natal.ascendant_sign = chart.ascendant_sign
                    natal.ascendant_ruler = chart.ascendant_ruler
                else:
                    natal = NatalChart(
                        user_id=user.id,
                        planets_json=chart_dict,
                        aspects_json=aspects_dict,
                        recommended_cards_json=recommended_dict,
                        ascendant_sign=chart.ascendant_sign,
                        ascendant_ruler=chart.ascendant_ruler,
                    )
                db.add(natal)
                
                await db.commit()
                print(f"Successfully updated User ID {user.id}. Recommended {len(recommended_dict)} cards.")

            except Exception as e:
                print(f"Error recalculating for user {user.id}: {e}")
                await db.rollback()

    print("\n--- Done ---")

if __name__ == "__main__":
    asyncio.run(recalculate_all())
