from __future__ import annotations
"""
Interpretation Engine — базовый класс агента-интерпретатора.

Каждое учение имеет своего агента-интерпретатора.
На старте активен только WesternAstrologyAgent.
"""

from abc import ABC, abstractmethod
from openai import AsyncOpenAI
import json
import logging

from app.dsb.interpreters.schemas import UniversalInsightSchema
from app.dsb.config import DSB_MODEL_FAST, DSB_TEMPERATURE_INTERPRETATION, DSB_MAX_TOKENS_INTERPRETATION

logger = logging.getLogger(__name__)


class InterpretationAgent(ABC):
    """
    Абстрактный агент-интерпретатор.

    Принимает raw_data от Calculator и генерирует список UIS-объектов.
    Каждый подкласс:
    - Определяет system_name
    - Определяет _build_system_prompt() — промпт для своего учения
    - Реализует interpret() если нужна нестандартная логика

    Модель для тестирования: gpt-4o-mini (меняется на Claude в продакшне).
    """

    system_name: str = ""
    model: str = DSB_MODEL_FAST
    temperature: float = DSB_TEMPERATURE_INTERPRETATION
    max_tokens: int = DSB_MAX_TOKENS_INTERPRETATION

    def __init__(self):
        self._client = AsyncOpenAI()

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """Возвращает system prompt для данного учения."""
        pass

    def _build_user_prompt(self, raw_data: dict) -> str:
        """Формирует user prompt из сырых данных."""
        return (
            f"Вот сырые расчётные данные учения '{self.system_name}':\n\n"
            f"```json\n{json.dumps(raw_data, ensure_ascii=False, indent=2)}\n```\n\n"
            "Интерпретируй каждый значимый элемент. "
            "Верни **только** JSON-массив объектов в формате Universal Insight Schema. "
            "Не добавляй пояснительный текст вне JSON."
        )

    async def interpret(self, raw_data: dict) -> list[UniversalInsightSchema]:
        """
        Интерпретирует сырые данные учения в список UIS-объектов.

        Вызывает LLM с system prompt + user prompt,
        парсит JSON-ответ в список UniversalInsightSchema.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(raw_data)

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

            # Ответ может быть {"insights": [...]} или напрямую [...]
            raw_list = parsed if isinstance(parsed, list) else parsed.get("insights", [])

            insights = []
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
