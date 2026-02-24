"""
AVATAR Telegram Bot (aiogram 3.x)
- /start → shows Mini App button
- Voice messages → Whisper → returns transcript
"""
import asyncio
import logging
import httpx

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, MINI_APP_URL, API_BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_router(bot: Bot) -> Dispatcher:
    """Build dispatcher with all handlers registered."""
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        """Handle /start command — show Mini App button."""
        await message.answer(
            "✨ <b>AVATAR</b> — платформа эволюции сознания\n\n"
            "Открой свою карту из 176 архетипов и начни путь трансформации через 8 сфер жизни.\n\n"
            "🌟 <b>Что тебя ждёт:</b>\n"
            "• Астрологический расчёт натальной карты\n"
            "• 176 карточек (22 архетипа × 8 сфер)\n"
            "• Синхронизация через 10 фаз погружения\n"
            "• Сессии выравнивания с AI-агентом\n"
            "• Шкала Хокинса от 20 до 1000\n"
            "• Геймификация: ✦ Энергия, XP, ранги\n\n"
            "Нажми кнопку ниже чтобы начать 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="🚀 Открыть AVATAR",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ]])
        )

    @dp.message(F.voice)
    async def handle_voice(message: Message):
        """Handle voice messages — transcribe via Whisper API."""
        await message.answer("🎙 Обрабатываю голосовое сообщение...")
        try:
            file_info = await bot.get_file(message.voice.file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

            async with httpx.AsyncClient(timeout=30) as client:
                audio_resp = await client.get(file_url)
                audio_bytes = audio_resp.content

                response = await client.post(
                    f"{API_BASE_URL}/api/voice",
                    data={
                        "user_id": str(message.from_user.id),
                        "session_type": "bot_voice",
                    },
                    files={"audio": ("voice.ogg", audio_bytes, "audio/ogg")},
                )
                result = response.json()
                transcript = result.get("transcript", "")

            if transcript:
                await message.answer(
                    f"📝 <b>Распознано:</b>\n\n{transcript}\n\n"
                    "Запись добавлена в ваш профиль."
                )
            else:
                await message.answer("❌ Не удалось распознать голос. Попробуйте ещё раз.")

        except Exception as e:
            logger.error(f"Voice error: {e}")
            await message.answer("❌ Ошибка обработки голосового. Попробуйте позже.")

    @dp.message(F.text)
    async def handle_text(message: Message):
        """Handle text messages — redirect to Mini App."""
        await message.answer(
            "💬 Все взаимодействия происходят в Mini App.\n\n"
            "Используй /start чтобы открыть приложение.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="🌟 Открыть AVATAR",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ]])
        )

    return dp


async def main():
    logger.info("Starting AVATAR bot...")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = build_router(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
