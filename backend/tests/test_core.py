"""
Tests for economy service and natal chart calculation.
"""
import pytest
from app.core.economy import (
    hawkins_to_rank, RANK_NAMES, get_sphere_awareness, calculate_xp_for_level
)


class TestHawkinsToRank:
    def test_sleeping(self):
        assert hawkins_to_rank(0) == 0
        assert hawkins_to_rank(100) == 0
        assert hawkins_to_rank(174) == 0

    def test_awakening(self):
        assert hawkins_to_rank(175) == 1
        assert hawkins_to_rank(200) == 1
        assert hawkins_to_rank(249) == 1

    def test_conscious(self):
        assert hawkins_to_rank(250) == 2
        assert hawkins_to_rank(350) == 2
        assert hawkins_to_rank(399) == 2

    def test_master(self):
        assert hawkins_to_rank(400) == 3
        assert hawkins_to_rank(500) == 3
        assert hawkins_to_rank(539) == 3

    def test_sage(self):
        assert hawkins_to_rank(540) == 4
        assert hawkins_to_rank(650) == 4
        assert hawkins_to_rank(699) == 4

    def test_enlightened(self):
        assert hawkins_to_rank(700) == 5
        assert hawkins_to_rank(1000) == 5

    def test_rank_names_complete(self):
        for rank in range(6):
            assert rank in RANK_NAMES


class TestSphereAwareness:
    def test_shadow(self):
        assert get_sphere_awareness(0) == "В тени"
        assert get_sphere_awareness(100) == "В тени"
        assert get_sphere_awareness(174) == "В тени"

    def test_awakening(self):
        assert get_sphere_awareness(175) == "Пробуждается"
        assert get_sphere_awareness(200) == "Пробуждается"

    def test_conscious(self):
        assert get_sphere_awareness(250) == "Осознана"

    def test_mastery(self):
        assert get_sphere_awareness(400) == "Мастерство"

    def test_wisdom(self):
        assert get_sphere_awareness(540) == "Мудрость"

    def test_enlightened(self):
        assert get_sphere_awareness(700) == "Просветлена"


class TestXPFormula:
    def test_level_1_zero_xp(self):
        assert calculate_xp_for_level(1) == 0

    def test_xp_grows_with_level(self):
        xp_10 = calculate_xp_for_level(10)
        xp_50 = calculate_xp_for_level(50)
        xp_100 = calculate_xp_for_level(100)
        assert xp_10 < xp_50 < xp_100

    def test_level_10_approx(self):
        # Level 10 should be ~500 XP per architecture spec
        assert 300 < calculate_xp_for_level(10) < 1000


class TestAspectCalculator:
    def test_conjunction(self):
        from app.core.astrology.aspect_calculator import angle_diff, calculate_aspects
        # 0° diff = conjunction
        assert angle_diff(0, 0) == 0
        assert angle_diff(350, 10) == pytest.approx(20)
        assert angle_diff(180, 0) == 180

    def test_aspects_symmetry(self):
        from app.core.astrology.aspect_calculator import angle_diff
        # angle_diff should be symmetric
        assert angle_diff(10, 130) == angle_diff(130, 10)

    def test_calculate_aspects_basic(self):
        from app.core.astrology.aspect_calculator import calculate_aspects
        planets = [
            {"name_en": "Sun", "degree": 0.0, "archetype_id": 19, "priority": "critical"},
            {"name_en": "Moon", "degree": 0.5, "archetype_id": 2, "priority": "critical"},  # ~conjunction
            {"name_en": "Saturn", "degree": 90.0, "archetype_id": 4, "priority": "critical"},  # square to Sun
        ]
        aspects = calculate_aspects(planets)
        assert len(aspects) > 0
        # Sun-Moon should be a conjunction
        sun_moon = [a for a in aspects if set([a.planet1, a.planet2]) == {"Sun", "Moon"}]
        assert len(sun_moon) == 1
        assert sun_moon[0].aspect_type == "conjunction"
