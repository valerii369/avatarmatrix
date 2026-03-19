"""
Analytics Agent (Background Intelligence):
- Runs daily at midnight (00:00)
- Analyzes user touches/interactions from the day
- Scores cards (264) based on resonance with user queries
- Manifests cards when score threshold is reached
- Generates weekly insight reports
- NO direct user communication — pure analysis layer
"""
import json
import logging
import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.common import client, settings
from app.models.card_progress import CardProgress, CardStatus
from app.models.user_evolution import UserEvolution
from app.models.identity_passport import IdentityPassport
from app.core.astrology.vector_matcher import match_text_to_archetypes

logger = logging.getLogger(__name__)

# Score threshold for AI-manifesting a card
AI_MANIFEST_THRESHOLD = 3.0


class AnalyticsAgent:
    """
    Background analytics agent for card scoring and pattern detection.
    Connected to RAG: Identity Passport (vector) + Evolution Passport (vector).
    """

    @staticmethod
    async def run_daily_analysis(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        Daily Midnight Job: Analyze all touches from today,
        score cards based on resonance, manifest if threshold reached.
        """
        # 1. Get User Evolution data
        evo_res = await db.execute(
            select(UserEvolution).where(UserEvolution.user_id == user_id)
        )
        evo = evo_res.scalar_one_or_none()
        if not evo or not evo.evolution_data:
            return {"status": "no_data", "cards_manifested": []}

        # 2. Filter today's touches
        today = datetime.date.today().isoformat()
        all_touches = evo.evolution_data.get("touches", [])
        today_touches = [
            t for t in all_touches
            if t.get("timestamp", "")[:10] == today
        ]

        if not today_touches:
            return {"status": "no_touches_today", "cards_manifested": []}

        # 3. Extract assistant messages for resonance scoring
        assistant_touches = [
            t for t in today_touches
            if t.get("type") == "ASSISTANT_MESSAGE"
        ]

        if not assistant_touches:
            return {"status": "no_assistant_touches", "cards_manifested": []}

        # 4. Aggregate sphere resonances from touches
        sphere_scores: Dict[str, float] = {}
        for touch in assistant_touches:
            payload = touch.get("payload", {})
            sphere = payload.get("sphere", "IDENTITY")
            increment = payload.get("resonance_increment", 0.0)
            sphere_scores[sphere] = sphere_scores.get(sphere, 0.0) + increment

        # 5. For top resonating spheres, find matching archetypes via vector search
        manifested_cards = []
        sorted_spheres = sorted(sphere_scores.items(), key=lambda x: x[1], reverse=True)

        for sphere, score in sorted_spheres[:3]:  # Top 3 resonating spheres
            if score < 0.5:  # Minimum resonance threshold
                continue

            # Build a composite query from user messages in this sphere
            sphere_messages = []
            for touch in assistant_touches:
                p = touch.get("payload", {})
                if p.get("sphere") == sphere:
                    sphere_messages.append(f"sphere:{sphere} resonance:{p.get('resonance_increment', 0)}")

            if not sphere_messages:
                continue

            # Vector match to find the best archetype
            composite_text = f"Запросы пользователя в сфере {sphere}: " + " | ".join(sphere_messages)
            matches = await match_text_to_archetypes(db, composite_text, top_k=3)

            for arch_id, match_sphere, match_score in matches:
                if match_sphere != sphere:
                    continue

                # Update CardProgress score
                cp_res = await db.execute(
                    select(CardProgress).where(
                        CardProgress.user_id == user_id,
                        CardProgress.archetype_id == arch_id,
                        CardProgress.sphere == sphere
                    )
                )
                cp = cp_res.scalar_one_or_none()
                if not cp:
                    cp = CardProgress(
                        user_id=user_id,
                        archetype_id=arch_id,
                        sphere=sphere,
                        status=CardStatus.LOCKED
                    )
                    db.add(cp)
                    await db.flush()

                # Increment AI score
                cp.ai_score = (cp.ai_score or 0.0) + score
                logger.info(f"AI Score updated: user={user_id}, sphere={sphere}, arch={arch_id}, score={cp.ai_score}")

                # Check threshold for manifestation
                if cp.ai_score >= AI_MANIFEST_THRESHOLD and cp.status == CardStatus.LOCKED:
                    cp.status = CardStatus.RECOMMENDED
                    cp.is_recommended_ai = True
                    manifested_cards.append({
                        "archetype_id": arch_id,
                        "sphere": sphere,
                        "ai_score": cp.ai_score,
                        "source": "analytics_daily"
                    })
                    logger.info(f"Card MANIFESTED by AI: user={user_id}, sphere={sphere}, arch={arch_id}")

                break  # One archetype per sphere per day

        await db.commit()

        return {
            "status": "completed",
            "touches_analyzed": len(today_touches),
            "sphere_resonances": sphere_scores,
            "cards_manifested": manifested_cards
        }

    @staticmethod
    async def generate_weekly_report(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        Generates a weekly insight report based on evolution data.
        Identifies hidden patterns, critical points, and key insights.
        """
        # 1. Get Evolution data
        evo_res = await db.execute(
            select(UserEvolution).where(UserEvolution.user_id == user_id)
        )
        evo = evo_res.scalar_one_or_none()
        if not evo or not evo.evolution_data:
            return {"report": "Недостаточно данных для формирования отчёта."}

        # 2. Get Identity Passport for context
        passport_res = await db.execute(
            select(IdentityPassport).where(IdentityPassport.user_id == user_id)
        )
        passport = passport_res.scalar_one_or_none()

        # 3. Collect last 7 days of touches
        week_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()
        all_touches = evo.evolution_data.get("touches", [])
        weekly_touches = [t for t in all_touches if t.get("timestamp", "") >= week_ago]
        session_progress = evo.evolution_data.get("session_progress", [])[-10:]

        # 4. Build analysis prompt
        passport_brief = ""
        if passport and passport.simplified_characteristics:
            passport_brief = json.dumps(passport.simplified_characteristics, ensure_ascii=False)

        prompt = f"""Ты — аналитический агент системы AVATAR. Проанализируй еженедельные данные пользователя.

ПАСПОРТ ЛИЧНОСТИ (кратко):
{passport_brief or 'Отсутствует'}

КАСАНИЯ ЗА НЕДЕЛЮ ({len(weekly_touches)} шт.):
{json.dumps(weekly_touches[:20], ensure_ascii=False, indent=2)}

ПРОГРЕСС СЕССИЙ:
{json.dumps(session_progress, ensure_ascii=False, indent=2)}

ЗАДАЧИ:
1. **Скрытые паттерны**: какие повторяющиеся темы или поведенческие паттерны ты видишь?
2. **Критические точки**: есть ли сферы, требующие внимания?
3. **Ключевые осознания**: что пользователь осознал за эту неделю?
4. **Рекомендация**: на чём стоит сфокусироваться на следующей неделе?
5. **Общий прогресс**: краткая оценка эволюции пользователя (1-2 предложения).

ФОРМАТ ОТВЕТА — JSON:
{{
  "hidden_patterns": ["паттерн 1", "паттерн 2"],
  "critical_points": ["точка 1"],
  "key_insights": ["осознание 1"],
  "focus_recommendation": "рекомендация на текст",
  "progress_summary": "Краткое резюме прогресса.",
  "overall_score": 0-100
}}"""

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            report = json.loads(response.choices[0].message.content)
            report["generated_at"] = datetime.datetime.utcnow().isoformat()
            report["touches_count"] = len(weekly_touches)
            return report
        except Exception as e:
            logger.error(f"Weekly Report Generation Error: {e}")
            return {"report": "Ошибка при генерации отчёта.", "error": str(e)}

    @staticmethod
    async def check_evolution_manifestation(db: AsyncSession, user_id: int) -> List[Dict]:
        """
        Checks if any card in a sphere qualifies for 'evolution manifestation':
        When a card reaches hawkins_peak >= 200, unlock the next priority card in that sphere.
        """
        manifested = []

        # Get all synced/aligned cards with high hawkins
        stmt = select(CardProgress).where(
            CardProgress.user_id == user_id,
            CardProgress.hawkins_peak >= 200,
            CardProgress.status.in_([CardStatus.SYNCED, CardStatus.ALIGNED])
        )
        result = await db.execute(stmt)
        high_cards = result.scalars().all()

        for card in high_cards:
            # Find next locked card in the same sphere by priority
            next_stmt = select(CardProgress).where(
                CardProgress.user_id == user_id,
                CardProgress.sphere == card.sphere,
                CardProgress.status == CardStatus.LOCKED,
                CardProgress.astro_priority.in_(["critical", "high", "medium"])
            ).order_by(
                # Priority ordering
                CardProgress.astro_priority.asc()  # critical < high < medium alphabetically
            ).limit(1)

            next_res = await db.execute(next_stmt)
            next_card = next_res.scalar_one_or_none()

            if next_card:
                next_card.status = CardStatus.RECOMMENDED
                next_card.is_recommended_portrait = True
                manifested.append({
                    "archetype_id": next_card.archetype_id,
                    "sphere": next_card.sphere,
                    "source": "evolution",
                    "triggered_by": card.archetype_id
                })

        if manifested:
            await db.commit()

        return manifested
