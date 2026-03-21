from __future__ import annotations
"""
DSB Configuration — конфигурация системы Digital Soul Blueprint.
ACTIVE_SYSTEMS определяет, какие учения передают данные в интерпретацию.
Все калькуляторы запускаются всегда (для сбора сырых данных).
"""

# ─── Активные учения (данные передаются в Слой 2) ───────────────────────────
# На старте только западная астрология, остальные только считают, не интерпретируют
ACTIVE_SYSTEMS: list[str] = ["western_astrology"]

# ─── Реестр всех учений ─────────────────────────────────────────────────────
SYSTEM_REGISTRY: dict = {
    "western_astrology": {
        "calculator": "app.dsb.calculators.western_astrology.WesternAstrologyCalculator",
        "agent": "app.dsb.interpreters.western_astrology_agent.WesternAstrologyAgent",
        "rag_collection": "books_western_astrology",
        "active": True,   # передаёт данные в интерпретацию
        "runs_calculator": True,
    },
    "vedic_astrology": {
        "calculator": "app.dsb.calculators.vedic_astrology.VedicAstrologyCalculator",
        "agent": "app.dsb.interpreters.vedic_astrology_agent.VedicAstrologyAgent",
        "rag_collection": "books_vedic_astrology",
        "active": False,  # только считает, не интерпретирует
        "runs_calculator": True,
    },
    "human_design": {
        "calculator": "app.dsb.calculators.human_design.HumanDesignCalculator",
        "agent": "app.dsb.interpreters.human_design_agent.HumanDesignAgent",
        "rag_collection": "books_human_design",
        "active": False,
        "runs_calculator": True,
    },
    "gene_keys": {
        "calculator": "app.dsb.calculators.gene_keys.GeneKeysCalculator",
        "agent": "app.dsb.interpreters.gene_keys_agent.GeneKeysAgent",
        "rag_collection": "books_gene_keys",
        "active": False,
        "runs_calculator": True,
    },
    "numerology": {
        "calculator": "app.dsb.calculators.numerology.NumerologyCalculator",
        "agent": "app.dsb.interpreters.numerology_agent.NumerologyAgent",
        "rag_collection": "books_numerology",
        "active": False,
        "runs_calculator": True,
    },
    "matrix_of_destiny": {
        "calculator": "app.dsb.calculators.matrix_of_destiny.MatrixOfDestinyCalculator",
        "agent": "app.dsb.interpreters.matrix_agent.MatrixAgent",
        "rag_collection": "books_matrix",
        "active": False,
        "runs_calculator": True,
    },
    "bazi": {
        "calculator": "app.dsb.calculators.bazi.BaziCalculator",
        "agent": "app.dsb.interpreters.bazi_agent.BaziAgent",
        "rag_collection": "books_bazi",
        "active": False,
        "runs_calculator": True,
    },
    "tzolkin": {
        "calculator": "app.dsb.calculators.tzolkin.TzolkinCalculator",
        "agent": "app.dsb.interpreters.tzolkin_agent.TzolkinAgent",
        "rag_collection": "books_tzolkin",
        "active": False,
        "runs_calculator": True,
    },
}

# ─── Модели (для тестирования используем gpt-4o-mini) ───────────────────────
DSB_MODEL_FAST: str = "gpt-4o-mini"       # Слои 2, 3a, 3d (Merger, Compressor, Interpretation)
DSB_MODEL_DEEP: str = "gpt-4o-mini"       # Слой 3b, 3c (Sphere Agents, Meta Agent)
# В продакшне заменить на: DSB_MODEL_DEEP = "claude-opus-4-6", DSB_MODEL_FAST = "claude-sonnet-4-6"

DSB_TEMPERATURE_INTERPRETATION: float = 0.3
DSB_TEMPERATURE_SYNTHESIS: float = 0.4

DSB_MAX_TOKENS_INTERPRETATION: int = 8000
DSB_MAX_TOKENS_SPHERE: int = 12000
DSB_MAX_TOKENS_META: int = 6000
DSB_MAX_TOKENS_COMPRESSOR: int = 4000

# ─── 12 Сфер ────────────────────────────────────────────────────────────────
SPHERE_NAMES: dict[int, str] = {
    1:  "Идентичность / Я",
    2:  "Ресурсы / Деньги / Ценности",
    3:  "Коммуникация / Мышление",
    4:  "Корни / Семья / Безопасность",
    5:  "Творчество / Самовыражение",
    6:  "Здоровье / Рутина / Служение",
    7:  "Отношения / Партнёрство",
    8:  "Трансформация / Глубина",
    9:  "Мировоззрение / Экспансия",
    10: "Призвание / Реализация",
    11: "Сообщество / Будущее",
    12: "Бессознательное / Духовность",
}

SPHERE_ASTRO_HOUSE: dict[int, int] = {i: i for i in range(1, 13)}
