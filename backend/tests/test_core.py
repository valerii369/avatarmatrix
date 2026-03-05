"""
Tests for economy service and natal chart calculation.
"""
import pytest
from app.core.economy import (
    hawkins_to_rank, RANK_NAMES, get_sphere_awareness, calculate_xp_for_level
)


class TestHawkinsToRank:
    def test_level_1(self):
        assert hawkins_to_rank(0) == 0  # Fallback for 0 or negative
        assert hawkins_to_rank(1) == 1
        assert hawkins_to_rank(20) == 1

    def test_level_2(self):
        assert hawkins_to_rank(21) == 2
        assert hawkins_to_rank(50) == 2

    def test_level_3(self):
        assert hawkins_to_rank(51) == 3
        assert hawkins_to_rank(100) == 3

    def test_level_4(self):
        assert hawkins_to_rank(101) == 4
        assert hawkins_to_rank(175) == 4

    def test_level_5(self):
        assert hawkins_to_rank(176) == 5
        assert hawkins_to_rank(200) == 5
        
    def test_level_6(self):
        assert hawkins_to_rank(201) == 6
        assert hawkins_to_rank(310) == 6
        
    def test_level_7(self):
        assert hawkins_to_rank(311) == 7
        assert hawkins_to_rank(400) == 7
        
    def test_level_8(self):
        assert hawkins_to_rank(401) == 8
        assert hawkins_to_rank(500) == 8
        
    def test_level_9(self):
        assert hawkins_to_rank(501) == 9
        assert hawkins_to_rank(600) == 9

    def test_level_10(self):
        assert hawkins_to_rank(601) == 10
        assert hawkins_to_rank(1000) == 10

    def test_rank_names_complete(self):
        for rank in range(11):
            assert rank in RANK_NAMES


class TestSphereAwareness:
    def test_shadow(self):
        assert get_sphere_awareness(0) == "В тени"
        assert get_sphere_awareness(50) == "В тени"
        assert get_sphere_awareness(174) == "В тени"

    def test_awakening(self):
        assert get_sphere_awareness(175) == "Пробуждается"
        assert get_sphere_awareness(199) == "Пробуждается"

    def test_conscious(self):
        assert get_sphere_awareness(200) == "Осознана"
        assert get_sphere_awareness(399) == "Осознана"

    def test_mastery(self):
        assert get_sphere_awareness(400) == "Мастерство"
        assert get_sphere_awareness(499) == "Мастерство"

    def test_wisdom(self):
        assert get_sphere_awareness(500) == "Мудрость"
        assert get_sphere_awareness(599) == "Мудрость"

    def test_enlightened(self):
        assert get_sphere_awareness(600) == "Просветлена"
        assert get_sphere_awareness(1000) == "Просветлена"


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
