"""
Portrait Builder: aggregates data from all completed sync sessions
to build a user's psychological portrait per sphere.
Used by the recommendation engine to suggest next cards.
"""
import json
from collections import Counter
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models import (
    CardProgress, SyncSession, AlignSession,
    UserPortrait, Pattern, Connection
)
from app.core.economy import hawkins_to_rank


async def build_portrait_for_sphere(
    db: AsyncSession,
    user_id: int,
    sphere: str,
) -> UserPortrait:
    """
    Aggregate all sync + align sessions for one sphere.
    Extracts body map, patterns, Hawkins timeline, average/min scores.
    """
    # Load all synced cards in sphere
    cards_result = await db.execute(
        select(CardProgress).where(
            CardProgress.user_id == user_id,
            CardProgress.sphere == sphere,
            CardProgress.sync_sessions_count > 0,
        )
    )
    cards = cards_result.scalars().all()

    # Load all sync sessions for this sphere
    sync_result = await db.execute(
        select(SyncSession).where(
            SyncSession.user_id == user_id,
            SyncSession.sphere == sphere,
            SyncSession.is_complete == True,
        ).order_by(SyncSession.created_at)
    )
    sync_sessions = sync_result.scalars().all()

    if not sync_sessions:
        portrait = await _get_or_create_portrait(db, user_id, sphere)
        return portrait

    # Aggregate cards_data
    cards_data = []
    all_tags: list[str] = []
    body_map: dict[str, list] = {}
    hawkins_timeline = []

    for session in sync_sessions:
        card_entry = {
            "archetype_id": session.archetype_id,
            "date": session.created_at.isoformat() if session.created_at else None,
            "core_belief": session.extracted_core_belief or "",
            "shadow_pattern": session.extracted_shadow_pattern or "",
            "body_anchor": session.extracted_body_anchor or "",
            "dominant_emotion": session.extracted_dominant_emotion or "",
            "hawkins": session.hawkins_score,
        }
        cards_data.append(card_entry)

        # Collect tags
        if session.extracted_tags:
            all_tags.extend(session.extracted_tags)

        # Body map
        anchor = session.extracted_body_anchor or ""
        if anchor:
            body_map.setdefault(anchor, []).append(session.archetype_id)

        # Hawkins timeline
        if session.hawkins_score:
            hawkins_timeline.append({
                "date": session.created_at.date().isoformat() if session.created_at else None,
                "score": session.hawkins_score,
                "archetype_id": session.archetype_id,
            })

    # Compute stats
    hawkins_scores = [s.hawkins_score for s in sync_sessions if s.hawkins_score]
    avg_hawkins = int(sum(hawkins_scores) / len(hawkins_scores)) if hawkins_scores else 0
    min_hawkins = min(hawkins_scores) if hawkins_scores else 0

    # Detect cross-sphere patterns (tags appearing ≥2 times)
    tag_counts = Counter(all_tags)
    patterns = [
        {"tag": tag, "count": count, "strength": min(count, 10)}
        for tag, count in tag_counts.most_common(10)
        if count >= 2
    ]

    # Update or create UserPortrait
    portrait = await _get_or_create_portrait(db, user_id, sphere)
    portrait.cards_data = cards_data
    portrait.patterns_json = patterns
    portrait.body_map_json = {k: v for k, v in body_map.items()}
    portrait.avg_hawkins = avg_hawkins
    portrait.min_hawkins = min_hawkins
    portrait.hawkins_timeline = hawkins_timeline
    db.add(portrait)

    # Update Pattern table (global user patterns)
    await _update_global_patterns(db, user_id, tag_counts)

    # Update card portrait recommendations
    await _update_portrait_recommendations(db, user_id, sphere, patterns, min_hawkins)

    await db.commit()
    return portrait


async def build_full_portrait(db: AsyncSession, user_id: int) -> dict:
    """Build portrait for all 8 spheres and detect cross-sphere connections."""
    SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]

    portraits = {}
    for sphere in SPHERES:
        portrait = await build_portrait_for_sphere(db, user_id, sphere)
        portraits[sphere] = {
            "avg_hawkins": portrait.avg_hawkins,
            "min_hawkins": portrait.min_hawkins,
            "patterns": portrait.patterns_json,
            "body_map": portrait.body_map_json,
            "hawkins_timeline": portrait.hawkins_timeline,
        }

    # Detect cross-sphere connections from patterns
    await _detect_cross_sphere_connections(db, user_id, portraits)

    return portraits


async def get_next_recommended_cards(
    db: AsyncSession,
    user_id: int,
    limit: int = 5,
) -> list[dict]:
    """
    Get top recommended cards for the user based on portrait.
    Priority:
    1. Cards with astro_priority=critical that are not yet synced
    2. Cards in the sphere with the lowest min_hawkins
    3. Cards connected to already-synced cards via aspects
    """
    # Load all card progress
    cards_result = await db.execute(
        select(CardProgress).where(CardProgress.user_id == user_id)
    )
    all_cards = cards_result.scalars().all()

    # Load portraits
    portraits_result = await db.execute(
        select(UserPortrait).where(UserPortrait.user_id == user_id)
    )
    portraits = {p.sphere: p for p in portraits_result.scalars().all()}

    recommendations = []

    # Rule 1: Critical astro cards not yet played
    critical_unplayed = [
        c for c in all_cards
        if c.astro_priority == "critical" and c.status in ("recommended", "locked")
    ]
    for card in critical_unplayed[:3]:
        recommendations.append({
            "card_id": card.id,
            "archetype_id": card.archetype_id,
            "sphere": card.sphere,
            "reason": f"🔴 Критически важная карта (астрология)",
            "priority": 1,
        })

    # Rule 2: Sphere with lowest min_hawkins that has unplayed recommended cards
    sphere_scores = [
        (p.sphere, p.min_hawkins)
        for p in portraits.values()
        if p.min_hawkins > 0
    ]
    if sphere_scores:
        worst_sphere = min(sphere_scores, key=lambda x: x[1])[0]
        worst_cards = [
            c for c in all_cards
            if c.sphere == worst_sphere and c.status == "recommended" and c.sync_sessions_count == 0
        ]
        for card in worst_cards[:2]:
            if not any(r["card_id"] == card.id for r in recommendations):
                recommendations.append({
                    "card_id": card.id,
                    "archetype_id": card.archetype_id,
                    "sphere": card.sphere,
                    "reason": f"🔮 Сфера требует внимания (мин. Хокинс: {portraits[worst_sphere].min_hawkins})",
                    "priority": 2,
                })

    # Rule 3: Fill remaining from high-priority unplayed
    high_unplayed = [
        c for c in all_cards
        if c.astro_priority in ("high", "medium") and c.status == "recommended"
        and not any(r["card_id"] == c.id for r in recommendations)
    ]
    for card in high_unplayed[:limit - len(recommendations)]:
        recommendations.append({
            "card_id": card.id,
            "archetype_id": card.archetype_id,
            "sphere": card.sphere,
            "reason": "✨ Рекомендовано астрологическим анализом",
            "priority": 3,
        })

    return recommendations[:limit]


# ─── Private helpers ──────────────────────────────────────────────────────────

async def _get_or_create_portrait(
    db: AsyncSession, user_id: int, sphere: str
) -> UserPortrait:
    result = await db.execute(
        select(UserPortrait).where(
            UserPortrait.user_id == user_id,
            UserPortrait.sphere == sphere,
        )
    )
    portrait = result.scalar_one_or_none()
    if not portrait:
        portrait = UserPortrait(user_id=user_id, sphere=sphere)
        db.add(portrait)
        await db.flush()
    return portrait


async def _update_global_patterns(
    db: AsyncSession, user_id: int, tag_counts: Counter
) -> None:
    """Upsert global Pattern records."""
    patterns_result = await db.execute(
        select(Pattern).where(Pattern.user_id == user_id)
    )
    existing = {p.tag: p for p in patterns_result.scalars().all()}

    for tag, count in tag_counts.items():
        if count < 2:
            continue
        if tag in existing:
            existing[tag].occurrences = count
            existing[tag].strength = min(count, 10)
            db.add(existing[tag])
        else:
            p = Pattern(user_id=user_id, tag=tag, strength=min(count, 10), occurrences=count)
            db.add(p)


async def _update_portrait_recommendations(
    db: AsyncSession, user_id: int, sphere: str,
    patterns: list[dict], min_hawkins: int,
) -> None:
    """Mark cards as portrait-recommended based on sphere patterns."""
    # Cards in this sphere that are still locked/recommended
    cards_result = await db.execute(
        select(CardProgress).where(
            CardProgress.user_id == user_id,
            CardProgress.sphere == sphere,
            CardProgress.sync_sessions_count == 0,
        )
    )
    cards = cards_result.scalars().all()

    # For now: mark top 3 un-synced cards with highest astro priority as portrait-recommended
    priority_order = {"critical": 0, "high": 1, "medium": 2, "additional": 3, None: 4}
    sorted_cards = sorted(cards, key=lambda c: priority_order.get(c.astro_priority, 4))

    for card in sorted_cards[:3]:
        card.is_recommended_portrait = True
        db.add(card)


async def _detect_cross_sphere_connections(
    db: AsyncSession, user_id: int, portraits: dict
) -> None:
    """Detect connections between spheres based on shared patterns."""
    SPHERES = list(portraits.keys())

    for i, sphere1 in enumerate(SPHERES):
        p1_patterns = set(p["tag"] for p in (portraits[sphere1].get("patterns") or []))

        for sphere2 in SPHERES[i + 1:]:
            p2_patterns = set(p["tag"] for p in (portraits[sphere2].get("patterns") or []))
            shared = p1_patterns & p2_patterns

            if not shared:
                continue

            # Check if connection already exists
            existing = await db.execute(
                select(Connection).where(
                    Connection.user_id == user_id,
                    Connection.sphere_1 == sphere1,
                    Connection.sphere_2 == sphere2,
                    Connection.connection_type == "pattern",
                )
            )
            conn = existing.scalar_one_or_none()

            label = f"Общий паттерн: {', '.join(list(shared)[:2])}"
            if conn:
                conn.strength = len(shared)
                conn.label = label
                db.add(conn)
            else:
                conn = Connection(
                    user_id=user_id,
                    archetype_id_1=0,
                    sphere_1=sphere1,
                    archetype_id_2=0,
                    sphere_2=sphere2,
                    connection_type="pattern",
                    label=label,
                    strength=len(shared),
                )
                db.add(conn)
