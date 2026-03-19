"""
Analytics Router: Background intelligence endpoints.
- POST /analytics/run-daily — manual trigger for daily analysis
- POST /analytics/run-weekly — manual trigger for weekly reports
- GET /analytics/weekly-report/{user_id} — get latest weekly report
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.agents.analytics_agent import AnalyticsAgent

router = APIRouter()


class AnalyticsRequest(BaseModel):
    user_id: int


@router.post("/run-daily")
async def run_daily_analysis(request: AnalyticsRequest, db: AsyncSession = Depends(get_db)):
    """Manual trigger for daily card scoring analysis."""
    user_res = await db.execute(select(User).where(User.id == request.user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await AnalyticsAgent.run_daily_analysis(db, request.user_id)

    # Check evolution manifestation too
    evolution_cards = await AnalyticsAgent.check_evolution_manifestation(db, request.user_id)
    result["evolution_manifested"] = evolution_cards

    return result


@router.post("/run-weekly")
async def run_weekly_report(request: AnalyticsRequest, db: AsyncSession = Depends(get_db)):
    """Manual trigger for weekly report generation."""
    user_res = await db.execute(select(User).where(User.id == request.user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    report = await AnalyticsAgent.generate_weekly_report(db, request.user_id)

    # Store report in evolution data for frontend access
    from app.models.user_evolution import UserEvolution
    from sqlalchemy.orm.attributes import flag_modified

    evo_res = await db.execute(
        select(UserEvolution).where(UserEvolution.user_id == request.user_id)
    )
    evo = evo_res.scalar_one_or_none()
    if evo:
        if "weekly_reports" not in evo.evolution_data:
            evo.evolution_data["weekly_reports"] = []
        evo.evolution_data["weekly_reports"].append(report)
        # Keep last 12 reports (3 months)
        evo.evolution_data["weekly_reports"] = evo.evolution_data["weekly_reports"][-12:]
        flag_modified(evo, "evolution_data")
        await db.commit()

    # Send to Telegram
    if user.tg_id and report.get("progress_summary"):
        from app.services.notification import NotificationService
        msg = (
            "📊 <b>Еженедельный отчёт AVATAR</b>\n\n"
            f"🔍 <b>Прогресс:</b> {report.get('progress_summary', '')}\n\n"
        )
        patterns = report.get("hidden_patterns", [])
        if patterns:
            msg += "🧩 <b>Скрытые паттерны:</b>\n"
            for p in patterns[:3]:
                msg += f"• {p}\n"
            msg += "\n"
        
        focus = report.get("focus_recommendation", "")
        if focus:
            msg += f"🎯 <b>Фокус на неделю:</b> {focus}\n"
        
        await NotificationService.send_tg_message(user.tg_id, msg)

    return report


@router.get("/weekly-report/{user_id}")
async def get_weekly_reports(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get stored weekly reports for the 'Отчёты' tab."""
    from app.models.user_evolution import UserEvolution

    evo_res = await db.execute(
        select(UserEvolution).where(UserEvolution.user_id == user_id)
    )
    evo = evo_res.scalar_one_or_none()
    if not evo or not evo.evolution_data:
        return {"reports": []}

    reports = evo.evolution_data.get("weekly_reports", [])
    return {"reports": reports}
