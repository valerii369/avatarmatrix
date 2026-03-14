from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.core.economy import get_claim_status, claim_manual_energy

router = APIRouter()

class ClaimResponse(BaseModel):
    success: bool
    new_energy: int
    message: str

@router.get("/status/{user_id}")
async def fetch_claim_status(user_id: int, db: AsyncSession = Depends(get_db)):
    """Check if user can claim free energy."""
    return await get_claim_status(db, user_id)

@router.post("/claim")
async def execute_claim(request: dict, db: AsyncSession = Depends(get_db)):
    """Claim +10✦ energy manually (12h cooldown)."""
    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
        
    success, new_energy = await claim_manual_energy(db, user_id)
    if not success:
        return {
            "success": False, 
            "new_energy": 0, 
            "message": "Энергия еще восстанавливается. Попробуйте позже."
        }
    
    return {
        "success": True, 
        "new_energy": new_energy, 
        "message": "Вы получили +10 ✦ Энергии!"
    }
