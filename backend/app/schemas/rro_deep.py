from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class PsychologicalPortrait(BaseModel):
    light: str = Field(..., description="Высшее проявление, таланты и естественные преимущества")
    shadow: str = Field(..., description="Слепые зоны, страхи, автоматизмы")

class DeepSphere(BaseModel):
    """
    Глубокая структура одной жизненной сферы (Level 2).
    """
    status: str = Field(..., description="Короткий архетипический маркер")
    pithy_summary: str = Field(..., description="Суть сферы в 1-2 предложениях")
    psychological_portrait: PsychologicalPortrait
    evolutionary_task: str = Field(..., description="Конкретный экзистенциальный урок")
    life_hacks: List[str] = Field(default_factory=list, description="Практические рекомендации")
    astrological_markers: List[str] = Field(default_factory=list, description="Технические обоснования (планеты, аспекты)")
    resonance_score: int = Field(default=50, ge=0, le=100, description="Уровень актуальности сферы")

class DeepRiverContent(BaseModel):
    """
    Контейнер для всех 12 сфер в формате Deep Sphere.
    """
    spheres: Dict[str, DeepSphere]
