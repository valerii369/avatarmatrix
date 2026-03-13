from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, AliasChoices

class Identity(BaseModel):
    """Суть человека, выраженная через живой язык."""
    summary: str = Field(..., validation_alias=AliasChoices("summary", "description"), description="Глубинное описание сути")
    core_archetype: str = Field(..., validation_alias=AliasChoices("core_archetype", "archetype"), description="Доминирующий архетип")
    narrative_role: str = Field(..., validation_alias=AliasChoices("narrative_role", "role"), description="Роль в текущем жизненном сюжете")
    energy_description: str = Field(..., validation_alias=AliasChoices("energy_description", "energy"), description="Как человек проявляется энергетически")
    archetypal_resonance: Dict[str, str] = Field(default_factory=dict, description="Отношение к ключевым силам")

class Psychology(BaseModel):
    """Внутренние процессы и динамика."""
    guiding_thoughts: List[str] = Field(default_factory=list)
    active_requests: List[str] = Field(default_factory=list)
    inner_tensions: List[str] = Field(default_factory=list)
    talents: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    somatic_anchors: List[str] = Field(default_factory=list, description="Телесные якоря и сигналы (напр. 'Сжатие в горле при лжи')")

class SphereNarrative(BaseModel):
    """Описание конкретной сферы жизни как главы книги."""
    state_description: str = Field(..., validation_alias=AliasChoices("state_description", "landscape", "description"), description="Нарратив состояния")
    active_conflict: Optional[str] = Field(None)
    central_symbols: List[str] = Field(default_factory=list)
    evolution_stage: str = Field("Развитие", validation_alias=AliasChoices("evolution_stage", "stage", "evolution"), description="Стадия развития")
    key_lesson: Optional[str] = Field(None, description="Текущий жизненный урок в этой сфере")

class UserPrintSchema(BaseModel):
    """
    THE HUB: Живая книга о внутреннем мире человека. 
    Никаких цифр, планет и технических терминов. Только смыслы.
    """
    identity: Identity = Field(...)
    psychology: Psychology = Field(default_factory=Psychology)
    spheres: Dict[str, SphereNarrative] = Field(default_factory=dict)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
