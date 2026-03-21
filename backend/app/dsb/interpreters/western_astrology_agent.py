from __future__ import annotations
"""
WesternAstrologyAgent — активный агент Слоя 2 для западной астрологии.

Единственный активный агент на старте.
Принимает JSON натальной карты, генерирует 40-80 UIS-объектов.
"""

import os
from app.dsb.interpreters.base import InterpretationAgent


_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "western_astrology.txt")

with open(_PROMPT_PATH, encoding="utf-8") as _f:
    _SYSTEM_PROMPT = _f.read()


class WesternAstrologyAgent(InterpretationAgent):
    """
    Агент-интерпретатор западной астрологии.

    Обрабатывает вывод WesternAstrologyCalculator,
    генерирует 40-80 UIS-объектов привязанных к 12 сферам.
    """

    system_name = "western_astrology"

    def _build_system_prompt(self) -> str:
        return _SYSTEM_PROMPT
