from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user_print import UserPrint
from app.schemas.user_print import UserPrintSchema

router = APIRouter()


@router.get("/{user_id}", response_model=UserPrintSchema)
async def get_master_hub(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns the Master Hub (О тебе) data for the user.
    """
    result = await db.execute(
        select(UserPrint).where(UserPrint.user_id == user_id)
    )
    user_print = result.scalar_one_or_none()

    if not user_print or not user_print.print_data:
        raise HTTPException(
            status_code=404,
            detail="Master Hub not found. Complete onboarding first."
        )

    from app.core.economy import get_claim_status
    energy_claim = await get_claim_status(db, user_id)

    # Safe schema construction — validate the stored data
    try:
        data = dict(user_print.print_data)
        data["energy_claim"] = energy_claim

        # Ensure polarities has all required fields (fallback for old records)
        dp = data.get("deep_profile_data", {})
        pol = dp.get("polarities", {})
        pol.setdefault("hidden_talents", [])
        pol.setdefault("drain_factors", [])
        pol.setdefault("core_strengths", [])
        pol.setdefault("shadow_aspects", [])
        dp["polarities"] = pol

        # Ensure social_interface has all required fields
        si = dp.get("social_interface", {})
        si.setdefault("worldview_stance", "В процессе синтеза")
        si.setdefault("communication_style", "Прямое и открытое")
        si.setdefault("karmic_lesson", "Самопознание через 12 сфер")
        dp["social_interface"] = si

        # Ensure portrait_summary has all required fields
        ps = data.get("portrait_summary", {})
        ps.setdefault("core_identity", "Твой паспорт формируется...")
        ps.setdefault("core_archetype", "Многогранная личность")
        ps.setdefault("narrative_role", "Исследователь")
        ps.setdefault("energy_type", "Универсальная")
        ps.setdefault("current_dynamic", "Интеграция 12 сфер")
        data["portrait_summary"] = ps

        data["deep_profile_data"] = dp
        data.setdefault("metadata", {})

        return UserPrintSchema(**data)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"MasterHub schema error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Data format error: {e}")
