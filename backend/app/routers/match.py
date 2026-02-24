from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Match, User

router = APIRouter()


@router.get("/{user_id}")
async def get_matches(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Match).where(
            (Match.user_id_1 == user_id) | (Match.user_id_2 == user_id)
        )
    )
    matches = result.scalars().all()
    return [
        {
            "id": m.id,
            "sphere": m.sphere,
            "status": m.status,
            "compatibility_score": m.compatibility_score,
            "match_reason": m.match_reason,
        }
        for m in matches
    ]
