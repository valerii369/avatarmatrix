from __future__ import annotations
"""Цолькин (Майя) Agent — PLANNED stub. Not active."""
from app.dsb.interpreters.base import InterpretationAgent


class TzolkinAgent(InterpretationAgent):
    """
    Цолькин (Майя) — агент интерпретации (PLANNED).
    Будет активирован после реализации калькулятора.
    """
    system_name = "tzolkin"

    def _build_system_prompt(self) -> str:
        return f"Ты — эксперт по {self.system_name}. (Промпт в разработке — Фаза 2/3)"

    async def interpret(self, raw_data: dict):
        return []  # Stub: returns empty until activated
