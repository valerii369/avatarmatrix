import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

async def test_key():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: No OPENAI_API_KEY found in .env")
        return
    
    print(f"Testing key: {api_key[:10]}...{api_key[-5:]}")
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        print("Success! GPT-4o-mini is working.")
    except Exception as e:
        print(f"Error with GPT-4o-mini: {e}")

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        print("Success! GPT-4o is working.")
    except Exception as e:
        print(f"Error with GPT-4o: {e}")

if __name__ == "__main__":
    asyncio.run(test_key())
