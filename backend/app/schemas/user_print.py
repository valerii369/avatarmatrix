from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class PortraitSummary(BaseModel):
    """Краткое поэтичное описание сути личности."""
    core_identity: str = Field(..., description="2-3 предложения о сути")
    core_archetype: str = Field(..., description="Ведущий архетип")
    energy_type: str = Field(..., description="Динамика жизненной силы")
    narrative_role: str = Field(..., description="Роль в жизненном мифе")
    current_dynamic: str = Field(..., description="Главный внутренний фокус/конфликт")

class Polarities(BaseModel):
    """Сильные и слабые стороны."""
    core_strengths: List[str] = Field(default_factory=list)
    hidden_talents: List[str] = Field(default_factory=list)
    shadow_aspects: List[str] = Field(default_factory=list)
    drain_factors: List[str] = Field(default_factory=list)

class SocialInterface(BaseModel):
    """Взаимодействие с миром."""
    worldview_stance: str = Field(..., description="Базовое мировоззрение")
    communication_style: str = Field(..., description="Паттерны общения")
    karmic_lesson: str = Field(..., description="Трансформационная задача")

class SphereStatus(BaseModel):
    """Статус отдельной сферы с глубокой детализацией."""
    status: str = Field(..., description="Стадия развития/Архетипический маркер")
    insight: str = Field(..., description="Краткая суть (pithy summary)")
    light: Optional[str] = Field(None, description="Светлая сторона")
    shadow: Optional[str] = Field(None, description="Теневая сторона")
    evolutionary_task: Optional[str] = Field(None, description="Эволюционная задача")
    life_hacks: List[str] = Field(default_factory=list, description="Рекомендации")
    resonance: int = Field(default=50, description="Заряженность сферы")

class DeepProfileData(BaseModel):
    """Глубинные данные профиля."""
    polarities: Polarities
    social_interface: SocialInterface
    spheres_status: Dict[str, SphereStatus]
    meta_patterns: List[Dict[str, Any]] = Field(default_factory=list)

class EnergyClaimStatus(BaseModel):
    """Статус сбора бесплатной энергии."""
    can_claim: bool
    next_claim_at: Optional[str] = None

class UserPrintSchema(BaseModel):
    """
    THE OCEAN: Unified Personal Passport.
    Synthesized from all 'Rivers' (Astro, Sync, Diary).
    """
    portrait_summary: PortraitSummary
    deep_profile_data: DeepProfileData
    energy_claim: Optional[EnergyClaimStatus] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
