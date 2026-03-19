from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user_print import UserPrint
from app.models.identity_passport import IdentityPassport
from app.schemas.user_print import UserPrintSchema

router = APIRouter()

@router.get("/{user_id}", response_model=UserPrintSchema)
async def get_master_hub(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns the Master Hub (Ocean) data for the user.
    """
    result = await db.execute(
        select(UserPrint).where(UserPrint.user_id == user_id)
    )
    user_print = result.scalar_one_or_none()
    
    if not user_print:
        raise HTTPException(status_code=404, detail="Master Hub not found for this user.")
    
    from app.core.economy import get_claim_status
    
    energy_claim = await get_claim_status(db, user_id)
    
    return UserPrintSchema(
        **user_print.print_data,
        energy_claim=energy_claim
    )


@router.get("/{user_id}/about")
async def get_about_me(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    'О тебе' endpoint: returns simplified characteristics + spheres brief
    from Identity Passport for the frontend 'About Me' section.
    """
    passport_res = await db.execute(
        select(IdentityPassport).where(IdentityPassport.user_id == user_id)
    )
    passport = passport_res.scalar_one_or_none()
    
    if not passport:
        return {
            "characteristics": {},
            "spheres_brief": {},
            "has_data": False
        }
    
    return {
        "characteristics": passport.simplified_characteristics or {},
        "spheres_brief": passport.spheres_brief or {},
        "has_data": bool(passport.simplified_characteristics or passport.spheres_brief)
    }


@router.get("/{user_id}/reports")
async def get_reports(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    'Отчёты' tab endpoint: returns stored weekly reports from UserEvolution.
    """
    from app.models.user_evolution import UserEvolution
    
    evo_res = await db.execute(
        select(UserEvolution).where(UserEvolution.user_id == user_id)
    )
    evo = evo_res.scalar_one_or_none()
    
    if not evo or not evo.evolution_data:
        return {"reports": [], "has_reports": False}
    
    reports = evo.evolution_data.get("weekly_reports", [])
    
    # Format for frontend display
    formatted_reports = []
    for r in reversed(reports):  # Newest first
        formatted_reports.append({
            "date": r.get("generated_at", ""),
            "progress_summary": r.get("progress_summary", ""),
            "overall_score": r.get("overall_score", 0),
            "hidden_patterns": r.get("hidden_patterns", []),
            "critical_points": r.get("critical_points", []),
            "key_insights": r.get("key_insights", []),
            "focus_recommendation": r.get("focus_recommendation", ""),
            "touches_count": r.get("touches_count", 0)
        })
    
    return {
        "reports": formatted_reports,
        "has_reports": len(formatted_reports) > 0
    }
