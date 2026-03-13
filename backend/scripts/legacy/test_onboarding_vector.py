import asyncio
from app.agents.onboarding_agent import extract_onboarding_cards

async def test():
    chat_history = [
        {"role": "assistant", "content": "С какой мыслью или состоянием ты проснулся сегодня?"},
        {"role": "user", "content": "Я чувствую, что ничего не добился и топчусь на месте. Мне кажется, я потерял смысл того, чем занимаюсь. Все вокруг делают карьеру, а я просто завис."},
        {"role": "assistant", "content": "Это очень тяжелое чувство. Что, по-твоему, заставляет тебя чувствовать, что ты \"топчешься на месте\", в то время как другие идут вперед?"},
        {"role": "user", "content": "Наверное, страх сделать ошибку. Я постоянно откладываю важные решения, потому что боюсь, что выберу не тот путь, и в итоге вообще ничего не выбираю."}
    ]
    
    print("Extracting cards...")
    cards = await extract_onboarding_cards(chat_history)
    print("Result:")
    import json
    print(json.dumps(cards, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test())
