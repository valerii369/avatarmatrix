from __future__ import annotations
"""
Merger — Слой 3a DSB.

Принимает все UIS-объекты от всех активных агентов (на старте — от одного),
группирует их по primary_sphere.

На старте (1 учение): работает как сортировщик.
При 8 учениях: объединяет 8 потоков, дедуплицирует.
"""

import logging
from collections import defaultdict
from app.dsb.interpreters.schemas import UniversalInsightSchema

logger = logging.getLogger(__name__)


class Merger:
    """
    Объединяет все UIS-объекты от всех активных агентов по сферам.
    Работает без LLM — чистая механическая сортировка по primary_sphere.
    """

    def merge(
        self, interpretations: list[list[UniversalInsightSchema]]
    ) -> dict[str, list[UniversalInsightSchema]]:
        """
        Принимает список списков UIS (от каждого агента) и группирует по сферам.

        Возвращает: {"sphere_1": [UIS...], "sphere_2": [...], ..., "sphere_12": [...]}
        """
        grouped: dict[str, list[UniversalInsightSchema]] = defaultdict(list)

        for agent_insights in interpretations:
            for insight in agent_insights:
                sphere_key = f"sphere_{insight.primary_sphere}"
                grouped[sphere_key].append(insight)

        # Убедиться что все 12 сфер представлены (даже пустые)
        result = {}
        for i in range(1, 13):
            key = f"sphere_{i}"
            # Сортировка: high → medium → low по influence_level
            sphere_insights = grouped.get(key, [])
            priority_map = {"high": 0, "medium": 1, "low": 2}
            sphere_insights.sort(key=lambda x: priority_map.get(x.influence_level, 1))
            result[key] = sphere_insights

        total = sum(len(v) for v in result.values())
        logger.info(f"[Merger] Grouped {total} UIS across 12 spheres")

        return result
