from __future__ import annotations
"""
Compressor — Слой 3d DSB.

Генерирует краткий формат портрета (1 абзац на сферу) из детального.
Запускается 1 раз после MetaAgent.
Модель: gpt-4o-mini.
"""

import os
import json
import logging
from openai import AsyncOpenAI

from app.dsb.config import DSB_MODEL_FAST, DSB_TEMPERATURE_INTERPRETATION, DSB_MAX_TOKENS_COMPRESSOR

logger = logging.getLogger(__name__)

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "compressor.txt")
with open(_PROMPT_PATH, encoding="utf-8") as _f:
    _SYSTEM_PROMPT = _f.read()


class Compressor:
    """
    Сжимает детальный 5-слойный портрет до краткого:
    1 абзац (3-5 предложений) на каждую из 12 сфер + 1 общий абзац.
    """

    def __init__(self):
        self._client = AsyncOpenAI()

    async def compress(
        self,
        sphere_portraits: list[dict],
        meta_patterns: dict,
    ) -> dict:
        """
        Генерирует краткий формат из детального портрета.

        Returns: {"sphere_1_brief": "...", ..., "overall_brief": "..."}
        """
        # Извлекаем ключевые паттерны по каждой сфере для компрессора
        sphere_summaries = []
        for sp in sphere_portraits:
            summary = {
                "sphere_num": sp.get("sphere_num"),
                "sphere_name": sp.get("sphere_name"),
                "top_patterns": [
                    p.get("pattern_name") + ": " + p.get("formula", "")
                    for p in sp.get("layer3_patterns", [])[:3]
                ],
                "top_recommendation": (
                    sp.get("layer4_recommendations", [{}])[0].get("text", "")
                    if sp.get("layer4_recommendations")
                    else ""
                ),
                "top_risk": (
                    sp.get("layer5_shadow_audit", [{}])[0].get("risk_name", "")
                    if sp.get("layer5_shadow_audit")
                    else ""
                ),
            }
            sphere_summaries.append(summary)

        meta_summary = [
            p.get("name", "") + ": " + p.get("description", "")[:100]
            for p in meta_patterns.get("meta_patterns", [])[:3]
        ]

        user_prompt = (
            "Вот данные для создания краткого портрета:\n\n"
            f"Сферы:\n```json\n{json.dumps(sphere_summaries, ensure_ascii=False, indent=2)}\n```\n\n"
            f"Суперпаттерны: {meta_summary}\n\n"
            "Создай краткий формат: 1 абзац (3-5 предложений) на каждую сферу + общий."
        )

        try:
            response = await self._client.chat.completions.create(
                model=DSB_MODEL_FAST,
                temperature=DSB_TEMPERATURE_INTERPRETATION,
                max_tokens=DSB_MAX_TOKENS_COMPRESSOR,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            logger.info(f"[Compressor] Brief portrait generated ({len(result)} keys)")
            return result

        except Exception as e:
            logger.error(f"[Compressor] Failed: {e}")
            return {"overall_brief": "Ошибка генерации краткого формата."}
