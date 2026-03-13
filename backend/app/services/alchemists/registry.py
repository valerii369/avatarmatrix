import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import os

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class RiverNarrative(BaseModel):
    """Модель 'Реки' — системно-специфичного нарратива по сферам."""
    system_name: str
    spheres: Dict[str, str] = Field(default_factory=dict)
    archetypal_hits: List[str] = Field(default_factory=list)

class BaseAlchemist(ABC):
    """
    Базовый класс для 'Алхимиков' — модулей, переводящих 'Дождь' (Rain) 
    в системную 'Реку' (River).
    """
    
    @abstractmethod
    def alchemy_name(self) -> str:
        """Уникальное имя учения (напр. 'WesternAstrology')."""
        pass

    @abstractmethod
    async def transmute(self, raw_data: Dict[str, Any]) -> RiverNarrative:
        """
        Трансформация сырых данных (Дождь) в системный нарратив (Река).
        """
        pass

class WesternAstrologyAlchemist(BaseAlchemist):
    """
    Алхимик Западной Классической Астрологии.
    Переводит положения планет (Дождь) в системную Реку смыслов.
    """
    def alchemy_name(self) -> str:
        return "WesternAstrology"

    async def transmute(self, raw_data: Dict[str, Any]) -> RiverNarrative:
        # raw_data здесь — это объекты из NatalChart (планеты, аспекты)
        
        prompt = f"""
ТЫ — ВЕДУЩИЙ АСТРОЛОГ СИСТЕМЫ AVATAR.
Твоя задача — превратить расчеты натальной карты (ДОЖДЬ) в качественный системный нарратив (РЕКА).

РАСЧЕТЫ (RAIN DATA):
{json.dumps(raw_data, ensure_ascii=False)}

КЛЮЧЕВАЯ ЗАДАЧА:
Для каждой из 12 сфер жизни создай 2-4 предложения глубокого психологического описания, основанного только на данных астрологии. 
НИКАКИХ ТЕХНИЧЕСКИХ ТЕРМИНОВ (запрещено упоминать планеты, знаки, дома в тексте). Пиши только про смыслы.

ВЕРНИ JSON СТРОГО В ФОРМАТЕ:
{{
  "spheres": {{
    "IDENTITY": "...",
    "RESOURCES": "...",
    ... (все 12 сфер)
  }},
  "archetypal_hits": ["Название архетипа 1", "Архетип 2"]
}}
"""
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return RiverNarrative(
                system_name=self.alchemy_name(),
                spheres=data.get("spheres", {}),
                archetypal_hits=data.get("archetypal_hits", [])
            )
        except Exception as e:
            print(f"Error in Astrology River creation: {e}")
            return RiverNarrative(system_name=self.alchemy_name())

class AlchemistRegistry:
    """
    Реестр для динамического подключения новых учений.
    """
    _alchemists: Dict[str, BaseAlchemist] = {}

    @classmethod
    def register(cls, alchemist: BaseAlchemist):
        cls._alchemists[alchemist.alchemy_name()] = alchemist

    @classmethod
    async def process_all(cls, generic_source_data: Dict[str, Any]) -> List[RiverNarrative]:
        """
        Прогоняет сырой 'Дождь' через всех алхимиков и собирает 'Реки'.
        """
        rivers = []
        for name, alchemist in cls._alchemists.items():
            if name in generic_source_data:
                river = await alchemist.transmute(generic_source_data[name])
                rivers.append(river)
        return rivers

# Регистрация
registry = AlchemistRegistry()
registry.register(WesternAstrologyAlchemist())
