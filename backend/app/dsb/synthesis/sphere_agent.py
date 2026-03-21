from __future__ import annotations
"""
SphereAgent — Слой 3b DSB.

Синтезирует 5-слойный портрет одной сферы из всех UIS-объектов для неё.
Запускается параллельно для всех 12 сфер.
Модель: gpt-4o-mini (в продакшне — Opus).
"""

import os
import json
import logging
from openai import AsyncOpenAI

from app.dsb.interpreters.schemas import UniversalInsightSchema
from app.dsb.config import (
    DSB_MODEL_DEEP,
    DSB_TEMPERATURE_SYNTHESIS,
    DSB_MAX_TOKENS_SPHERE,
    SPHERE_NAMES,
    ACTIVE_SYSTEMS,
)

logger = logging.getLogger(__name__)

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "sphere_agent.txt")
with open(_PROMPT_PATH, encoding="utf-8") as _f:
    _SYSTEM_PROMPT = _f.read()


class SphereAgent:
    """
    Агент синтеза одной сферы. Запускается 12 раз параллельно (по одному на сферу).
    Генерирует 5-слойную структуру.
    """

    def __init__(self):
        self._client = AsyncOpenAI()

    async def synthesize(
        self,
        sphere_num: int,
        insights: list[UniversalInsightSchema],
        active_systems: list[str] | None = None,
    ) -> dict:
        """
        Генерирует 5-слойный синтез для одной сферы.

        Args:
            sphere_num: номер сферы (1-12)
            insights: список UIS-объектов для этой сферы
            active_systems: список активных учений (влияет на промпт)
        """
        active_systems = active_systems or ACTIVE_SYSTEMS
        sphere_name = SPHERE_NAMES.get(sphere_num, f"Сфера {sphere_num}")

        if not insights:
            logger.warning(f"[SphereAgent #{sphere_num}] No insights provided")
            return self._empty_sphere(sphere_num, sphere_name)

        # Адаптация промпта под количество учений
        system_prompt = _SYSTEM_PROMPT
        if len(active_systems) == 1:
            system_prompt += (
                "\n\nВАЖНО: Сейчас активно ОДНО учение. "
                "В Слое 2 ищи ВНУТРИСИСТЕМНЫЕ связи — как разные элементы "
                "одного учения подтверждают или противоречат друг другу. "
                "convergence_score = степень внутренней согласованности элементов."
            )
        else:
            system_prompt += (
                f"\n\nВАЖНО: Активно {len(active_systems)} учений: {', '.join(active_systems)}. "
                "В Слое 2 ищи МЕЖСИСТЕМНЫЕ связи — где разные учения "
                "указывают на одно и то же. convergence_score = доля систем, согласных."
            )

        # Формируем список инсайтов для передачи в LLM
        insights_json = [
            {
                "source_system": i.source_system,
                "position": i.position,
                "primary_sphere": i.primary_sphere,
                "influence_level": i.influence_level,
                "light_aspect": i.light_aspect,
                "shadow_aspect": i.shadow_aspect,
                "core_theme": i.core_theme,
                "developmental_task": i.developmental_task,
                "triggers": i.triggers,
                "weight": i.weight,
            }
            for i in insights
        ]

        user_prompt = (
            f"Синтезируй данные для СФЕРЫ {sphere_num} — \"{sphere_name}\".\n\n"
            f"Количество входных факторов: {len(insights_json)}\n"
            f"Активные учения: {active_systems}\n\n"
            f"Факторы:\n```json\n{json.dumps(insights_json, ensure_ascii=False, indent=2)}\n```"
        )

        try:
            response = await self._client.chat.completions.create(
                model=DSB_MODEL_DEEP,
                temperature=DSB_TEMPERATURE_SYNTHESIS,
                max_tokens=DSB_MAX_TOKENS_SPHERE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            result["sphere_num"] = sphere_num
            result["sphere_name"] = sphere_name
            result["input_insight_count"] = len(insights)

            logger.info(
                f"[SphereAgent #{sphere_num}] Synthesized sphere '{sphere_name}' "
                f"from {len(insights)} insights"
            )
            return result

        except Exception as e:
            logger.error(f"[SphereAgent #{sphere_num}] Synthesis failed: {e}")
            return self._empty_sphere(sphere_num, sphere_name)

    @staticmethod
    def _empty_sphere(sphere_num: int, sphere_name: str) -> dict:
        return {
            "sphere_num": sphere_num,
            "sphere_name": sphere_name,
            "input_insight_count": 0,
            "layer1_facts": [],
            "layer2_chains": [],
            "layer3_patterns": [],
            "layer4_recommendations": [],
            "layer5_shadow_audit": [],
            "error": "No insights available for synthesis",
        }
