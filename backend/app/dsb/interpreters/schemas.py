from __future__ import annotations
"""
Universal Insight Schema (UIS) — единый формат выхода для всех агентов-интерпретаторов.

Каждый агент Слоя 2 возвращает список UIS-объектов.
Формат универсален для всех 8 учений.
"""

from typing import Literal, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class UniversalInsightSchema(BaseModel):
    """
    Универсальная схема инсайта — единица интерпретации любого учения.
    Один объект = один значимый элемент расчёта (планета, аспект, канал и т.д.)
    """

    id: str = Field(default_factory=lambda: str(uuid4()))

    # ─── Источник ────────────────────────────────────────────────────────────
    source_system: str
    # Пример: "western_astrology", "bazi", "human_design"

    position: str
    # Описание позиции/элемента. Пример: "Venus retrograde in Aquarius in 10th House"

    # ─── Привязка к сферам (1-12) ─────────────────────────────────────────
    spheres_affected: list[int] = Field(default_factory=list)
    # Все сферы, которые затрагивает данный элемент (1-12)

    primary_sphere: int = Field(ge=1, le=12)
    # Основная сфера (главная привязка)

    # ─── Уровень влияния ─────────────────────────────────────────────────
    influence_level: Literal["high", "medium", "low"]
    # high: Солнце/Луна, точный аспект орб<2°, управитель дома, День-Мастер
    # medium: личные планеты, аспекты 2-5°
    # low: внешние планеты без личных аспектов, широкие аспекты

    polarity: Literal["light", "shadow", "dual"]
    # Полярность: light=сила, shadow=тень, dual=оба аспекта

    # ─── Содержание (на русском языке) ────────────────────────────────────
    light_aspect: str
    # Потенциал, дар, ресурс. Минимум 3 предложения.

    shadow_aspect: str
    # Тень, ловушка, риск. Минимум 3 предложения.

    energy_description: str
    # Энергетический профиль позиции.

    core_theme: str
    # Ключевая тема в краткой формулировке.

    developmental_task: str
    # Задача развития: что нужно проработать.

    integration_key: str
    # Ключ интеграции: как использовать энергию.

    triggers: list[str] = Field(default_factory=list)
    # Конкретные жизненные ситуации, активирующие данный элемент.

    timing: Optional[str] = None
    # Временной аспект: когда проявляется наиболее сильно.

    book_references: list[str] = Field(default_factory=list)
    # Ссылки на книги из RAG-базы. Формат: "Author:Book:pXXX"

    # ─── Метрики ──────────────────────────────────────────────────────────
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    # Уверенность LLM в интерпретации.

    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    # Вес элемента (из расчёта: орб, достоинство, центральность).

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "source_system": "western_astrology",
                "position": "Venus retrograde in Aquarius in 10th House",
                "spheres_affected": [1, 7, 10],
                "primary_sphere": 10,
                "influence_level": "high",
                "polarity": "dual",
                "light_aspect": "Способность притягивать ресурсы через нестандартное позиционирование...",
                "shadow_aspect": "Сложные отношения с признанием: хочет его, но не умеет принимать...",
                "energy_description": "Эстетика свободы, ценности сообщества...",
                "core_theme": "Переосмысление системы ценностей",
                "developmental_task": "Найти свою модель признания, не чужую",
                "integration_key": "Принять, что нестандартность — это привлекательность",
                "triggers": ["Ситуации с чужими стандартами успеха"],
                "timing": "Активируется после 28-30 лет",
                "book_references": ["Liz Greene:Saturn:p.214"],
                "confidence": 0.88,
                "weight": 0.85,
            }
        }
