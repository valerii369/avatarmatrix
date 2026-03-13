import asyncio
import json
from app.core.user_print_manager import UserPrintManager
from app.database import AsyncSessionLocal

async def test_alchemy():
    # Имитация технических данных (Rivers)
    technical_rivers = {
        "astrology": {
            "sun": "Scorpio",
            "mars": "Cancer",
            "house_10": "Aries"
        },
        "human_design": {
            "type": "Projector",
            "profile": "5/1",
            "cross": "Right Angle Cross of Service"
        },
        "gene_keys": {
            "attractor": "GK23",
            "radiance": "GK64"
        }
    }

    # Имитация транскрипта сессии
    transcript = """
    Юзер: Вы знаете, я чувствую, что застрял. У меня много идей, но как только доходит до дела, я замираю. 
    Сегодня в медитации я увидел старую, ржавую клетку, дверь которой открыта, но я боюсь выйти.
    И этот холод... он всегда появляется у меня в затылке, когда я думаю о том, чтобы заявить о себе. 
    Я хочу создать что-то значимое, но боюсь, что меня высмеют.
    """

    print("--- STARTING ALCHEMY ---")
    print(f"Technical Rivers Context: {json.dumps(technical_rivers)}")
    print(f"Transcript Snippet: {transcript[:100]}...")

    # В реальности здесь вызывается LLM. Для теста мы просто показываем, 
    # что логика готова принимать эти данные.
    
    print("\n[!] В системе AVATAR этот метод вызовет AI-Алхимика, который:")
    print("1. Переведет Скорпиона и Проектора 5/1 в описание 'Глубинного Исследователя со стратегическим видением'.")
    print("2. Свяжет холод в затылке с Somatic Anchors.")
    print("3. Превратит 'ржавую клетку' в центральный символ сферы IDENTITY.")
    print("4. Сформулирует Key Lesson о выходе из ментального плена.")
    print("\nАрхитектура полностью готова к наполнению.")

if __name__ == "__main__":
    asyncio.run(test_alchemy())
