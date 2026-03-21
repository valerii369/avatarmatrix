from __future__ import annotations
"""Ba Zi (Four Pillars) Calculator — PLANNED (Phase 2). Stub implementation."""
from app.dsb.calculators.base import Calculator, BirthData


class BaziCalculator(Calculator):
    """
    Ба Цзы (Четыре Столпа) — PLANNED (Фаза 2).
    4 столпа (год/месяц/день/час), скрытые стволы, 10 Божеств,
    баланс 5 стихий, столпы удачи.
    Источники: китайский солнечный календарь, таблицы Ган Чжи.
    """
    system_name = "bazi"

    async def calculate(self, birth_data: BirthData) -> dict:
        # TODO: Phase 2 — implement using Chinese Solar Calendar / Gan Zhi tables
        raw_data = {
            "status": "stub",
            "note": "Ba Zi calculator not yet implemented. Planned for Phase 2.",
            "day_master": None,
            "pillars": {
                "year": {"stem": None, "branch": None, "hidden_stems": []},
                "month": {"stem": None, "branch": None, "hidden_stems": []},
                "day": {"stem": None, "branch": None, "hidden_stems": []},
                "hour": {"stem": None, "branch": None, "hidden_stems": []},
            },
            "ten_gods": {},
            "five_elements_balance": {},
            "luck_pillars": [],
        }
        return self._base_envelope(birth_data, raw_data)
