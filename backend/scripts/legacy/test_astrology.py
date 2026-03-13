import asyncio
from datetime import datetime
from app.core.astrology.natal_chart import calculate_natal_chart, to_dict as chart_to_dict
from app.core.astrology.aspect_calculator import calculate_aspects, to_dict as aspects_to_dict
from app.core.astrology.priority_engine import generate_recommended_cards, to_dict as cards_to_dict

async def main():
    # Pick a random date, e.g., Albert Einstein: March 14, 1879, 11:30 AM, Ulm, Germany
    # Ulm is ~ 48.3984 N, 9.9915 E, tz: Europe/Berlin
    birth_date = datetime(1879, 3, 14)
    chart = calculate_natal_chart(birth_date, "11:30", 48.3984, 9.9915, "Europe/Berlin")
    
    chart_dict = chart_to_dict(chart)
    print("--- PLANETS ---")
    for p in chart_dict["planets"]:
        print(f"{p['name_en']:<10} | {p['sign']:<11} | House: {p['house']:<2} | Speed: {p.get('speed', 0):>8.4f} | Stat: {p.get('is_stationary')} | Decan Ruler: {p.get('decan_ruler')}")

    aspects = calculate_aspects(chart_dict["planets"])
    aspects_dict = aspects_to_dict(aspects)
    
    print("\n--- ASPECTS ---")
    for a in aspects_dict:
        print(f"{a['planet1']} {a['type']} {a['planet2']} | Orb: {a['orb']} | Exact: {a.get('is_exact')} | Applying: {a.get('is_applying')} | Label: {a['label']}")

    cards = generate_recommended_cards(chart)
    cards_list = cards_to_dict(cards)
    print("\n--- RECOMMENDED CARDS (Top 10) ---")
    for c in cards_list[:10]:
        print(f"Priority: {c['priority']:<10} | Sphere: {c['sphere']:<10} | Arch: {c['archetype_id']:<2} | Reason: {c['reason']}")

if __name__ == "__main__":
    asyncio.run(main())
