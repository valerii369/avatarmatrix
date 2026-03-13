from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.data_architecture import Event
from app.agents.evolution_agent import EvolutionAgent

router = APIRouter()

class EventRequest(BaseModel):
    user_id: int
    session_id: Optional[int] = None
    event_type: str
    payload: Dict[str, Any]

@router.post("/event")
async def log_event(request: EventRequest, db: AsyncSession = Depends(get_db)):
    """
    Logs raw telemetry events (Layer 1).
    Used for tracking pauses, scrolls, and other behavioral signals.
    """
    new_event = Event(
        user_id=request.user_id,
        session_id=request.session_id,
        event_type=request.event_type,
        payload_json=request.payload
    )
    db.add(new_event)
    await db.commit()
    return {"status": "event_logged"}

@router.post("/evolve")
async def trigger_evolution(db: AsyncSession = Depends(get_db)):
    """
    Manually triggers the evolutionary cycle for the textual scene library.
    """
    await EvolutionAgent.evolve_text_library(db)
    return {"status": "text_evolution_triggered"}
