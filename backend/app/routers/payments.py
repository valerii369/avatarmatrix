import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.core.economy import award_energy, REFERRAL_PURCHASE_BONUS

logger = logging.getLogger(__name__)

router = APIRouter()

class PaymentOffer(BaseModel):
    id: str
    name: str
    energy: int
    price_usd: float
    stars: int

OFFERS = [
    PaymentOffer(id="pack_100", name="100 ✦ Энергии", energy=100, price_usd=1.0, stars=100),
    PaymentOffer(id="pack_300", name="300 ✦ Энергии", energy=300, price_usd=2.94, stars=294), # 2% off
    PaymentOffer(id="pack_500", name="500 ✦ Энергии", energy=500, price_usd=4.75, stars=475), # 5% off
    PaymentOffer(id="pack_1000", name="1000 ✦ Энергии", energy=1000, price_usd=9.0, stars=900), # 10% off
    PaymentOffer(id="pack_premium", name="AVATAR Premium + 1000 ✦", energy=1000, price_usd=8.0, stars=800), # 20% off
]

class InvoiceRequest(BaseModel):
    user_id: int
    offer_id: str

@router.get("/offers", response_model=list[PaymentOffer])
async def get_offers():
    """Get available energy packs."""
    return OFFERS

@router.post("/create-invoice")
async def create_invoice(request: InvoiceRequest, db: AsyncSession = Depends(get_db)):
    """Create a Telegram Stars invoice link."""
    from app.config import settings
    import httpx
    
    offer = next((o for o in OFFERS if o.id == request.offer_id), None)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payload = f"{user.id}:{offer.id}"
    
    description = f"Пополнение баланса на {offer.energy} ✦ Энергии" if offer.energy > 0 else "Активация Premium доступа ко всем функциям"
    
    async with httpx.AsyncClient() as client:
        url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/createInvoiceLink"
        req_data = {
            "title": offer.name,
            "description": description,
            "payload": payload,
            "provider_token": "",  # STARRY PAYMENTS (XTR) REQUIRE EMPTY PROVIDER TOKEN
            "currency": "XTR",
            "prices": [{"label": "Цена", "amount": offer.stars}]
        }
        resp = await client.post(url, json=req_data)
        
        data = resp.json()
        if not data.get("ok"):
            logger.error(f"TG PAYMENT ERROR for user {request.user_id}: {data}")
            raise HTTPException(status_code=500, detail=f"TG Error: {data.get('description')}")
            
        return {"invoice_link": data["result"]}

class PaymentVerifyRequest(BaseModel):
    user_id: int
    offer_id: str
    payload: str

@router.post("/verify")
async def verify_payment(request: PaymentVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Backend verify after successful payment."""
    offer = next((o for o in OFFERS if o.id == request.offer_id), None)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await award_energy(db, user, "manual", amount=offer.energy)
    
    if user.referred_by:
        referrer_result = await db.execute(select(User).where(User.id == user.referred_by))
        referrer = referrer_result.scalar_one_or_none()
        if referrer:
            await award_energy(db, referrer, "referral_purchase")
            
    await db.commit()
    await db.refresh(user)
    
    return {"success": True, "new_energy": user.energy}
