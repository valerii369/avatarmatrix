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
    PaymentOffer(id="pack_1000", name="1000 ✦ Энергии", energy=1000, price_usd=1.9, stars=100),
    PaymentOffer(id="pack_2500", name="2500 ✦ Энергии", energy=2500, price_usd=3.9, stars=250),
    PaymentOffer(id="pack_5000", name="5000 ✦ Энергии", energy=5000, price_usd=6.9, stars=500),
    PaymentOffer(id="pack_premium", name="AVATAR Premium", energy=0, price_usd=6.0, stars=330),
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
            "currency": "XTR",
            "prices": [{"label": "Цена", "amount": offer.stars}]
        }
        resp = await client.post(url, json=req_data)
        
        data = resp.json()
        if not data.get("ok"):
            print(f"TG PAYMENT ERROR: {data}")  # Basic log to console/journal
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
