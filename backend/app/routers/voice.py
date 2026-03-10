import io
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.database import get_db
from app.models import VoiceRecord
from app.config import settings

router = APIRouter()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@router.post("")
async def transcribe_voice(
    user_id: int = Form(...),
    session_type: str = Form(default="general"),
    session_id: int = Form(default=None),
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe voice audio using OpenAI Whisper."""
    audio_bytes = await audio.read()

    try:
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio.filename or "voice.ogg", io.BytesIO(audio_bytes), audio.content_type or "audio/ogg"),
            language="ru",
        )
        text = transcript.text
        text = transcript.text
    except Exception as e:
        print(f"ERROR VOICE: Whisper error: {e}")
        raise HTTPException(status_code=500, detail=f"Whisper error: {e}")

    # Save record
    try:
        record = VoiceRecord(
            user_id=user_id,
            transcript=text,
            session_type=session_type,
            session_id=session_id,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        await db.refresh(record)
    except Exception as e:
        print(f"ERROR VOICE: DB error: {e}")
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    return {"id": record.id, "transcript": text}
