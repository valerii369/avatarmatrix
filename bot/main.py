"""
AVATAR Telegram Bot (aiogram 3.x)
- /start   → shows Mini App button
- /reset   → wipes user birth data (for testing restart flow)
- /restart → triggers full natal chart recalculation
- Voice    → Whisper transcription
"""
import asyncio
import logging
import httpx

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, MINI_APP_URL, API_BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _open_btn(label: str = "🌟 Открыть AVATAR") -> InlineKeyboardMarkup:
    """Reusable Mini App open button."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=label, web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


def build_router(bot: Bot) -> Dispatcher:
    """Build dispatcher with all handlers registered."""
    dp = Dispatcher()

    # ── /start ──────────────────────────────────────────────────────────────
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
            reply_markup=_open_btn("🚀 Открыть AVATAR"),
            parse_mode="HTML",
        )

    # ── /reset ───────────────────────────────────────────────────────────────
    @dp.message(Command("reset"))
    async def cmd_reset(message: Message):
        """Handle /reset — wipe user birth data and cards so onboarding runs again."""
        tg_id = message.from_user.id
        await message.answer("⚠️ Сбрасываю данные профиля...")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{API_BASE_URL}/api/profile/tg/{tg_id}/reset")

            if resp.status_code == 200:
                await message.answer(
                    "✅ <b>Профиль сброшен.</b>\n\n"
                    "Дата, время и место рождения удалены.\n"
                    "Все 176 карточек очищены.\n\n"
                    "👇 <b>Что делать дальше:</b>\n"
                    "Нажми кнопку ниже — при входе в приложение "
                    "тебя встретит онбординг для повторного ввода данных.",
                    reply_markup=_open_btn("📋 Пройти онбординг заново"),
                    parse_mode="HTML",
                )
            elif resp.status_code == 404:
                await message.answer(
                    "❌ Профиль не найден.\n\n"
                    "Сначала пройди регистрацию в приложении.",
                    reply_markup=_open_btn("🚀 Открыть AVATAR"),
                )
            else:
                await message.answer(
                    f"❌ Ошибка сброса (код {resp.status_code}):\n<code>{resp.text[:300]}</code>",
                    parse_mode="HTML",
                )

        except httpx.ConnectError:
            await message.answer(
                "❌ Не удалось подключиться к серверу.\n\n"
                f"<b>API:</b> <code>{API_BASE_URL}</code>\n\n"
                "Убедись, что бэкенд запущен.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Reset error: {e}")
            await message.answer(f"❌ Непредвиденная ошибка: <code>{str(e)[:200]}</code>", parse_mode="HTML")

    # ── /restart ─────────────────────────────────────────────────────────────
    @dp.message(Command("restart"))
    async def cmd_restart(message: Message):
        """Handle /restart — force recalculate natal chart."""
        tg_id = message.from_user.id
        await message.answer("🔄 Запускаю пересчёт натальной карты...")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # 1. Fetch user profile
                user_resp = await client.get(f"{API_BASE_URL}/api/profile/tg/{tg_id}")
                if user_resp.status_code == 404:
                    await message.answer(
                        "❌ Профиль не найден.\n\nСначала пройди регистрацию.",
                        reply_markup=_open_btn("🚀 Открыть AVATAR"),
                    )
                    return
                if user_resp.status_code != 200:
                    await message.answer(f"❌ Ошибка получения профиля (код {user_resp.status_code}).")
                    return

                user_data = user_resp.json()

                if not user_data.get("birth_date") or not user_data.get("birth_place"):
                    await message.answer(
                        "❌ Данные рождения не заполнены.\n\n"
                        "Пройди онбординг в приложении, затем используй /restart.",
                        reply_markup=_open_btn("📋 Ввести данные"),
                    )
                    return

                # 2. Trigger recalculation
                birth_date = user_data["birth_date"]
                if "T" in birth_date:
                    birth_date = birth_date.split("T")[0]

                calc_resp = await client.post(
                    f"{API_BASE_URL}/api/calc",
                    json={
                        "user_id": user_data["id"],
                        "birth_date": birth_date,
                        "birth_time": user_data.get("birth_time") or "12:00",
                        "birth_place": user_data["birth_place"],
                    },
                )

                if calc_resp.status_code == 200:
                    calc_data = calc_resp.json()
                    total = calc_data.get("total_cards", 176)
                    await message.answer(
                        f"✅ <b>Карта пересчитана!</b>\n\n"
                        f"📊 Открыто архетипов: <b>{total}</b>\n"
                        f"📅 Дата: <b>{birth_date}</b>\n"
                        f"📍 Место: <b>{user_data['birth_place']}</b>\n\n"
                        "Открой приложение чтобы увидеть новые приоритеты 🌟",
                        reply_markup=_open_btn("🌟 Открыть AVATAR"),
                        parse_mode="HTML",
                    )
                else:
                    await message.answer(
                        f"❌ Ошибка пересчёта (код {calc_resp.status_code}):\n"
                        f"<code>{calc_resp.text[:300]}</code>",
                        parse_mode="HTML",
                    )

        except httpx.ConnectError:
            await message.answer(
                "❌ Не удалось подключиться к серверу.\n\n"
                f"<b>API:</b> <code>{API_BASE_URL}</code>",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Restart error: {e}")
            await message.answer(f"❌ Непредвиденная ошибка: <code>{str(e)[:200]}</code>", parse_mode="HTML")

    # ── Voice ─────────────────────────────────────────────────────────────────
    @dp.message(F.voice)
    async def handle_voice(message: Message):
        """Handle voice messages — transcribe via Whisper API."""
        await message.answer("🎙 Обрабатываю голосовое сообщение...")
        try:
            file_info = await bot.get_file(message.voice.file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

            async with httpx.AsyncClient(timeout=60) as client:
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
                    f"📝 <b>Распознано:</b>\n\n{transcript}",
                    parse_mode="HTML",
                )
            else:
                await message.answer("❌ Не удалось распознать голос. Попробуйте ещё раз.")

        except Exception as e:
            logger.error(f"Voice error: {e}")
            await message.answer("❌ Ошибка обработки голосового. Попробуйте позже.")

    # ── Catchall text (NOT commands) ──────────────────────────────────────────
    @dp.message(F.text & ~F.text.startswith("/"))
    async def handle_text(message: Message):
        """Handle plain text messages — redirect to Mini App."""
        await message.answer(
            "💬 Все взаимодействия происходят в Mini App.\n\n"
            "Доступные команды:\n"
            "/start — открыть приложение\n"
            "/restart — пересчитать карту\n"
            "/reset — сбросить профиль (тест)",
            reply_markup=_open_btn("🚀 Открыть AVATAR"),
        )

    return dp


async def main():
    logger.info(f"Starting AVATAR bot (API: {API_BASE_URL})...")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = build_router(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
