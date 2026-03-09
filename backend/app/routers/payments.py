from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.core.economy import award_energy, REFERRAL_PURCHASE_BONUS

router = APIRouter()

class PaymentOffer(BaseModel):
    id: str
    name: str
    energy: int
    price_usd: float
    stars: int

OFFERS = [
    PaymentOffer(id="starter_pack", name="Starter Pack", energy=5000, price_usd=6.0, stars=290),
    PaymentOffer(id="medium_topup", name="Medium Top-up", energy=2000, price_usd=3.0, stars=145),
    PaymentOffer(id="small_topup", name="Small Top-up", energy=1000, price_usd=1.5, stars=75),
]

class PaymentVerifyRequest(BaseModel):
    user_id: int
    offer_id: str
    payload: str  # In real TG payments, this is the verification payload

@router.get("/offers", response_model=list[PaymentOffer])
async def get_offers():
    """Get available energy packs."""
    return OFFERS

@router.post("/verify")
async def verify_payment(request: PaymentVerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    Mock verification for Telegram Stars payments.
    In production, this would verify the Telegram payment signal.
    """
    offer = next((o for o in OFFERS if o.id == request.offer_id), None)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Award energy from the pack
    await award_energy(db, user, "manual", amount=offer.energy)
    
    # Process referral purchase bonus (if user was referred)
    if user.referred_by:
        referrer_result = await db.execute(select(User).where(User.id == user.referred_by))
        referrer = referrer_result.scalar_one_or_none()
        if referrer:
            await award_energy(db, referrer, "referral_purchase")
            
    await db.commit()
    
    return {"success": True, "new_energy": user.energy}
