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
    Returns the Master Hub (Ocean) data for the user.
    """
    result = await db.execute(
        select(UserPrint).where(UserPrint.user_id == user_id)
    )
    user_print = result.scalar_one_or_none()
    
    if not user_print:
        # If no print exists, return a default empty state or 404
        # For now, let's return 404 or an empty skeleton if preferred.
        # Given the flow, calc or onboarding should have created it.
        raise HTTPException(status_code=404, detail="Master Hub not found for this user.")
    
    from app.core.economy import get_claim_status
    
    energy_claim = await get_claim_status(db, user_id)
    
    return UserPrintSchema(
        **user_print.print_data,
        energy_claim=energy_claim
    )
