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

    async def interpret(self, raw_data: dict) -> list[UniversalInsightSchema]:
        import asyncio
        import json
        import logging
        from app.dsb.rag.retriever import retrieve
        from app.dsb.interpreters.schemas import UniversalInsightSchema

        logger = logging.getLogger(__name__)

        # 1. Формируем запросы
        queries = []
        for p in raw_data.get("planets", []):
            queries.append(f"{p.get('name')} in {p.get('sign')} in {p.get('house')} house")
        for a in raw_data.get("aspects", []):
            queries.append(f"{a.get('planet1')} {a.get('type')} {a.get('planet2')}")

        # 2. Ищем в Qdrant контекст
        search_tasks = [retrieve(q, "books_western_astrology", top_k=2) for q in queries[:20]]
        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        context_chunks = {}
        for res in results:
            if isinstance(res, list):
                for hit in res:
                    chunk_id = hit["text"][:50]
                    if chunk_id not in context_chunks:
                        context_chunks[chunk_id] = f"Source ({hit['book_title']} by {hit['author']}):\n{hit['text']}"

        # Ограничиваем количество чанков (топ 10)
        selected_chunks = list(context_chunks.values())[:10]
        context_text = "\n\n---\n\n".join(selected_chunks) if selected_chunks else "Контекст не найден."

        # 3. Формируем промпт
        system_prompt = self._build_system_prompt()
        user_prompt = (
            f"Вот сырые расчётные данные учения '{self.system_name}':\n\n"
            f"```json\n{json.dumps(raw_data, ensure_ascii=False, indent=2)}\n```\n\n"
            f"КОНТЕКСТ ИЗ РЕАЛЬНЫХ КНИГ (ОБЯЗАТЕЛЬНО ИСПОЛЬЗОВАТЬ):\n"
            f"{context_text}\n\n"
            "Интерпретируй каждый значимый элемент, опираясь на контекст книг. "
            "Верни **только** JSON-массив объектов в формате Universal Insight Schema. "
            "Не добавляй пояснительный текст вне JSON."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            parsed = json.loads(content)
            raw_list = parsed if isinstance(parsed, list) else parsed.get("insights", [])

            insights = []
            from app.dsb.interpreters.schemas import UniversalInsightSchema
            for item in raw_list:
                try:
                    insights.append(UniversalInsightSchema(**item))
                except Exception as e:
                    logger.warning(f"[{self.system_name}] Failed to parse UIS item: {e}")

            logger.info(f"[{self.system_name}] Generated {len(insights)} UIS objects")
            return insights

        except Exception as e:
            logger.error(f"[{self.system_name}] Interpretation failed: {e}")
            return []
