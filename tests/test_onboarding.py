import asyncio
import httpx
import json

from app.database import AsyncSessionLocal
from app.models import User
from sqlalchemy import select

async def run_test():
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).limit(1))
        user = user.scalar_one_or_none()
        if not user:
            print("No users found in database.")
            return
        user_id = user.id
        print(f"Using test user ID: {user_id}")
    
    chat_history = [
        {"role": "user", "content": "Привет! Я готов к диагностике и узнать какие у меня активные архетипы."},
        {"role": "assistant", "content": "Привет! Что для тебя сейчас важнее всего?"},
        {"role": "user", "content": "Хочу найти свое предназначение, мне важна самореализация."},
        {"role": "assistant", "content": "А как насчет отношений с другими людьми?"},
        {"role": "user", "content": "Отношения тоже важны, но я больше сфокусирован на миссии."},
        {"role": "assistant", "content": "Понял. Что-то еще?"},
        {"role": "user", "content": "Нет, это всё. Я хорошо чувствую людей и анализирую."},
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # First test if calc endpoint works
        print("Calling /api/onboarding/ai/calculate")
        resp = await client.post("http://localhost:8000/api/onboarding/ai/calculate", json={
            "user_id": user_id,
            "chat_history": chat_history
        })
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    asyncio.run(run_test())
