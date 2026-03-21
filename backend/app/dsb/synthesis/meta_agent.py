from __future__ import annotations
"""
MetaAgent — Слой 3c DSB.

Находит межсферные суперпаттерны — "красные нити",
пронизывающие несколько сфер жизни человека.
Запускается 1 раз после всех 12 SphereAgents.
Модель: gpt-4o-mini (в продакшне — Opus).
"""

import os
import json
import logging
from openai import AsyncOpenAI

from app.dsb.config import DSB_MODEL_DEEP, DSB_TEMPERATURE_SYNTHESIS, DSB_MAX_TOKENS_META

logger = logging.getLogger(__name__)

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "meta_agent.txt")
with open(_PROMPT_PATH, encoding="utf-8") as _f:
    _SYSTEM_PROMPT = _f.read()


class MetaAgent:
    """
    Анализирует все 12 синтезированных сфер и находит
    3-7 межсферных суперпаттернов.
    """

    def __init__(self):
        self._client = AsyncOpenAI()

    async def find_patterns(self, sphere_portraits: list[dict]) -> dict:
        """
        Принимает все 12 синтезированных сфер и генерирует суперпаттерны.

        Args:
            sphere_portraits: список из 12 dict от SphereAgent

        Returns:
            {"meta_patterns": [...]}
        """
        # Компрессия данных для передачи в LLM (ключевые части каждой сферы)
        compressed_spheres = []
        for sp in sphere_portraits:
            compressed = {
                "sphere_num": sp.get("sphere_num"),
                "sphere_name": sp.get("sphere_name"),
                "patterns": [
                    {"name": p.get("pattern_name"), "formula": p.get("formula")}
                    for p in sp.get("layer3_patterns", [])[:3]
                ],
                "top_risks": [
                    r.get("risk_name")
                    for r in sp.get("layer5_shadow_audit", [])[:2]
                ],
            }
            compressed_spheres.append(compressed)

        user_prompt = (
            "Вот синтезированные данные по всем 12 сферам портрета:\n\n"
            f"```json\n{json.dumps(compressed_spheres, ensure_ascii=False, indent=2)}\n```\n\n"
            "Найди 3-7 межсферных суперпаттернов — архетипических тем, "
            "пронизывающих несколько сфер."
        )

        try:
            response = await self._client.chat.completions.create(
                model=DSB_MODEL_DEEP,
                temperature=DSB_TEMPERATURE_SYNTHESIS,
                max_tokens=DSB_MAX_TOKENS_META,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            meta_patterns = result.get("meta_patterns", [])
            logger.info(f"[MetaAgent] Found {len(meta_patterns)} meta-patterns")
            return {"meta_patterns": meta_patterns}

        except Exception as e:
            logger.error(f"[MetaAgent] Failed: {e}")
            return {"meta_patterns": []}
