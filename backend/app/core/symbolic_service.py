import json
import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.portrait import UserSymbol
from app.agents.common import client, settings

logger = logging.getLogger(__name__)

class SymbolicService:
    _global_symbols: Dict[str, Any] = None

    @classmethod
    def load_global_symbols(cls):
        if cls._global_symbols is None:
            path = os.path.join(settings.DATA_DIR, "global_symbols.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._global_symbols = json.load(f)
            else:
                cls._global_symbols = {}
        return cls._global_symbols

    @classmethod
    async def extract_symbols_from_text(cls, text: str) -> List[str]:
        """Uses LLM to identify key diagnostic symbols in user's speech."""
        globals = cls.load_global_symbols()
        symbol_list = ", ".join(globals.keys())
        
        prompt = f"""ПРОАНАЛИЗИРУЙ ТЕКСТ И ВЫДЕЛИ КЛЮЧЕВЫЕ ОБРАЗЫ (СИМВОЛЫ).
СПИСОК ИЗВЕСТНЫХ СИСТЕМЕ СИМВОЛОВ: {symbol_list}

ТЕКСТ:
{text}

ЗАДАЧА:
1. Выдели символы из списка, которые упомянул пользователь.
2. Добавь НОВЫЕ важные образы, которые кажутся значимыми для подсознания (метафоры, странные объекты).

ОТВЕТЬ В JSON:
{{
  "identified_symbols": ["key", "forest", "etc"],
  "new_symbols": ["сломанный забор", "летящая птица"]
}}
"""
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return list(set(result.get("identified_symbols", []) + result.get("new_symbols", [])))
        except Exception as e:
            logger.error(f"Symbol Extraction Error: {e}")
            return []

    @classmethod
    async def get_symbolic_context(
        cls, db: AsyncSession, user_id: int, transcript_text: str, sphere: str
    ) -> str:
        """
        Builds a comprehensive symbolic context for the Analytic Agent.
        Combines Global symbols and Personal user history.
        """
        symbols = await cls.extract_symbols_from_text(transcript_text)
        if not symbols:
            return "Символы не обнаружены."

        global_dict = cls.load_global_symbols()
        
        # 1. Fetch Personal Symbols from DB
        stmt = select(UserSymbol).where(
            UserSymbol.user_id == user_id,
            UserSymbol.symbol.in_(symbols)
        )
        res = await db.execute(stmt)
        personal_symbols = {ps.symbol: ps for ps in res.scalars().all()}

        context_lines = ["\nСИМВОЛИЧЕСКИЙ СЛОВАРЬ ЭТОЙ СЕССИИ:\n"]
        
        for sym in symbols:
            # Personal override first
            if sym in personal_symbols:
                ps = personal_symbols[sym]
                context_lines.append(f"- 【{sym}】 (ЛИЧНЫЙ): {ps.interpretation} (Заряд: {ps.emotional_charge})")
            # Global lookup second
            elif sym in global_dict:
                info = global_dict[sym]
                interp = info.get("spheres", {}).get(sphere, info.get("universal"))
                context_lines.append(f"- 【{sym}】 (ОБЩИЙ): {interp}")
            else:
                context_lines.append(f"- 【{sym}】: Значение требует выявления в этой сессии.")

        return "\n".join(context_lines)

    @classmethod
    async def update_personal_symbols(
        cls, db: AsyncSession, user_id: int, identified_symbols: Dict[str, str], sphere: str
    ):
        """Saves or updates personal symbol interpretations after analysis."""
        for sym, interpretation in identified_symbols.items():
            stmt = select(UserSymbol).where(
                UserSymbol.user_id == user_id, 
                UserSymbol.symbol == sym.lower()
            )
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            
            if existing:
                # Simple merge logic for now
                existing.interpretation = f"{existing.interpretation} | UPD: {interpretation}"
                existing.occurrences += 1
            else:
                new_sym = UserSymbol(
                    user_id=user_id,
                    symbol=sym.lower(),
                    interpretation=interpretation,
                    sphere=sphere
                )
                db.add(new_sym)
        
        await db.commit()
