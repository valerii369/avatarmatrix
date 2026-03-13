from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class IdentityModel(BaseModel):
    """Модель базовой идентичности (The Hub Core)."""
    summary: str = Field(..., description="Глубинное резюме личности")
    core_archetype: str = Field(..., description="Центральный архетип")
    narrative_role: str = Field(..., description="Текущая роль в сюжете жизни")
    energy_description: str = Field(..., description="Описание энергетического профиля")
    archetypal_resonance: Dict[str, str] = Field(default_factory=dict, description="Резонанс с ключевыми концептами (Власть, Любовь и т.д.)")

class PsychologyModel(BaseModel):
    """Модель психологического состояния."""
    guiding_thoughts: List[str] = Field(default_factory=list, description="Ведущие мысли")
    active_requests: List[str] = Field(default_factory=list, description="Актуальные запросы")
    inner_tensions: List[str] = Field(default_factory=list, description="Внутренние напряжения/конфликты")
    talents: List[str] = Field(default_factory=list, description="Сильные стороны")
    limitations: List[str] = Field(default_factory=list, description="Ограничения и тени")
    somatic_anchors: List[str] = Field(default_factory=list, description="Телесные якоря")

class SphereModel(BaseModel):
    """Модель отдельной сферы жизни (главы Книги)."""
    state_description: str = Field(..., description="Нарративное описание состояния сферы")
    active_conflict: Optional[str] = Field(None, description="Текущий активный конфликт")
    central_symbols: List[str] = Field(default_factory=list, description="Ключевые символы")
    evolution_stage: str = Field(..., description="Стадия эволюции в данной сфере")
    key_lesson: Optional[str] = Field(None, description="Главный жизненный урок сейчас")

class HubMetadata(BaseModel):
    """Метаданные хаба."""
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    update_count: int = 0

class MasterHubSchema(BaseModel):
    """Глобальный Хаб Пользователя (The Book of a Human)."""
    user_id: str
    identity: IdentityModel
    psychology: PsychologyModel
    spheres: Dict[str, SphereModel]
    metadata: HubMetadata = Field(default_factory=HubMetadata)

    class Config:
        from_attributes = True
