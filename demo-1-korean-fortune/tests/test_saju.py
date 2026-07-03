"""Tests for the Saju (Four Pillars) calculation.

Validates the Heavenly Stems / Earthly Branches computation with known dates
and ensures bilingual output works correctly.
"""

from __future__ import annotations

import pytest

from src.activities.saju import (
    _day_stem_branch,
    _hour_branch_index,
    _hour_stem_index,
    _month_branch_index,
    _month_stem_index,
    _year_branch_index,
    _year_stem_index,
    EARTHLY_BRANCHES_EN,
    EARTHLY_BRANCHES_KO,
    HEAVENLY_STEMS_EN,
    HEAVENLY_STEMS_KO,
    calculate_saju,
)
from src.models import Language, UserInput

# ── Unit tests for internal functions ────────────────────────────────────────


class TestYearStemBranch:
    """Test year-based Heavenly Stem and Earthly Branch calculations."""

    def test_year_2024_stem(self):
        """2024: (2024-4) % 10 = 0 -> 갑(甲) / Gap (Wood+)"""
        assert _year_stem_index(2024) == 0

    def test_year_2024_branch(self):
        """2024: (2024-4) % 12 = 4 -> 진(辰) Dragon"""
        assert _year_branch_index(2024) == 4

    def test_year_1990_stem(self):
        """1990: (1990-4) % 10 = 6 -> 경(庚) / Gyeong (Metal+)"""
        assert _year_stem_index(1990) == 6

    def test_year_1990_branch(self):
        """1990: (1990-4) % 12 = 6 -> 오(午) Horse"""
        assert _year_branch_index(1990) == 6

    def test_year_2000_stem(self):
        """2000: (2000-4) % 10 = 6 -> 경(庚) / Gyeong (Metal+)"""
        assert _year_stem_index(2000) == 6

    def test_year_2000_branch(self):
        """2000: (2000-4) % 12 = 4 -> 진(辰) Dragon"""
        assert _year_branch_index(2000) == 4

    def test_cycle_repeats_every_60_years(self):
        """The full sexagenary cycle repeats every 60 years."""
        for year in range(1900, 2100):
            assert _year_stem_index(year) == _year_stem_index(year + 60)
            assert _year_branch_index(year) == _year_branch_index(year + 60)

    def test_stem_range(self):
        """Stem index should always be 0-9."""
        for year in range(1900, 2100):
            assert 0 <= _year_stem_index(year) <= 9

    def test_branch_range(self):
        """Branch index should always be 0-11."""
        for year in range(1900, 2100):
            assert 0 <= _year_branch_index(year) <= 11


class TestMonthCalculation:
    def test_month_branch_range(self):
        """Month branch should always be 0-11."""
        for month in range(1, 13):
            assert 0 <= _month_branch_index(month) <= 11

    def test_month_stem_range(self):
        """Month stem should always be 0-9."""
        for y_stem in range(10):
            for month in range(1, 13):
                assert 0 <= _month_stem_index(y_stem, month) <= 9


class TestDayCalculation:
    def test_day_stem_branch_range(self):
        """Day stem/branch should be in valid ranges."""
        from datetime import date
        d = date(1990, 5, 15)
        stem, branch = _day_stem_branch(d)
        assert 0 <= stem <= 9
        assert 0 <= branch <= 11

    def test_consecutive_days_increment(self):
        """Consecutive days should have consecutive stem/branch values."""
        from datetime import date, timedelta
        d1 = date(2024, 1, 1)
        d2 = d1 + timedelta(days=1)
        s1, b1 = _day_stem_branch(d1)
        s2, b2 = _day_stem_branch(d2)
        assert s2 == (s1 + 1) % 10
        assert b2 == (b1 + 1) % 12

    def test_day_cycle_repeats_every_60_days(self):
        """The day pillar cycle repeats every 60 days."""
        from datetime import date, timedelta
        d = date(2024, 3, 1)
        s1, b1 = _day_stem_branch(d)
        s2, b2 = _day_stem_branch(d + timedelta(days=60))
        assert s1 == s2
        assert b1 == b2


class TestHourCalculation:
    def test_midnight_is_rat(self):
        """Hour 0 (midnight) should be Rat (子) = branch index 0 (shifted by 1 -> 0)."""
        # 00:00 -> (0+1)%24 = 1, 1//2 = 0 -> index 0 (子/Rat)
        assert _hour_branch_index(0) == 0

    def test_23_is_rat(self):
        """Hour 23 should also be Rat (子) since 子 spans 23:00-01:00."""
        # 23:00 -> (23+1)%24 = 0, 0//2 = 0 -> index 0 (子/Rat)
        assert _hour_branch_index(23) == 0

    def test_noon_is_horse(self):
        """Hour 12 (noon) should be Horse (午) = branch index 6."""
        # 12:00 -> (12+1)%24 = 13, 13//2 = 6 -> index 6 (午/Horse)
        assert _hour_branch_index(12) == 6

    def test_hour_branch_range(self):
        """Hour branch should always be 0-11."""
        for h in range(24):
            assert 0 <= _hour_branch_index(h) <= 11

    def test_hour_stem_range(self):
        """Hour stem should always be 0-9."""
        for day_stem in range(10):
            for h_branch in range(12):
                assert 0 <= _hour_stem_index(day_stem, h_branch) <= 9


# ── Integration tests for the calculate_saju activity ────────────────────────


class TestCalculateSajuActivity:
    """Test the full activity function (requires activity context)."""

    @pytest.mark.asyncio
    async def test_saju_korean_output(self):
        """Test that Korean language produces Korean-formatted output."""
        from unittest.mock import patch

        user = UserInput(
            name="테스트",
            birth_date="1990-05-15",
            language=Language.KO,
        )

        # Mock the activity context since we're testing outside Temporal
        with patch("temporalio.activity.logger"):
            result = await calculate_saju(user)

        # Year pillar for 1990: stem=6 (경/庚), branch=6 (오/午)
        assert "경(庚)" in result.year_pillar
        assert "오(午)" in result.year_pillar

        # Element should be in Korean
        assert any(elem in result.element for elem in ["목(木)", "화(火)", "토(土)", "금(金)", "수(水)"])

        # Interpretation should be in Korean
        assert any(char in result.interpretation for char in ["기운", "에너지", "성격", "존재", "의지"])

        # All four pillars should be present
        assert result.year_pillar
        assert result.month_pillar
        assert result.day_pillar
        assert result.hour_pillar

    @pytest.mark.asyncio
    async def test_saju_english_output(self):
        """Test that English language produces English-formatted output."""
        from unittest.mock import patch

        user = UserInput(
            name="Test",
            birth_date="1990-05-15",
            language=Language.EN,
        )

        with patch("temporalio.activity.logger"):
            result = await calculate_saju(user)

        # Year pillar for 1990: stem=6 -> Gyeong (Metal+), branch=6 -> O (Horse)
        assert "Gyeong" in result.year_pillar
        assert "Horse" in result.year_pillar

        # Element should be in English
        assert result.element in ["Wood", "Fire", "Earth", "Metal", "Water"]

        # Interpretation should be in English
        assert "born with the energy of" in result.interpretation

    @pytest.mark.asyncio
    async def test_saju_with_birth_time(self):
        """Test that providing birth time changes the hour pillar."""
        from unittest.mock import patch

        user_morning = UserInput(
            name="Test",
            birth_date="1990-05-15",
            birth_time="06:00",
            language=Language.EN,
        )
        user_evening = UserInput(
            name="Test",
            birth_date="1990-05-15",
            birth_time="22:00",
            language=Language.EN,
        )

        with patch("temporalio.activity.logger"):
            result_morning = await calculate_saju(user_morning)
            result_evening = await calculate_saju(user_evening)

        # Different birth times should produce different hour pillars
        assert result_morning.hour_pillar != result_evening.hour_pillar

        # But the year, month, and day pillars should be the same
        assert result_morning.year_pillar == result_evening.year_pillar
        assert result_morning.month_pillar == result_evening.month_pillar
        assert result_morning.day_pillar == result_evening.day_pillar

    @pytest.mark.asyncio
    async def test_saju_default_hour(self):
        """Without birth time, default to noon (午/Horse)."""
        from unittest.mock import patch

        user_no_time = UserInput(
            name="Test",
            birth_date="1990-05-15",
            language=Language.EN,
        )
        user_noon = UserInput(
            name="Test",
            birth_date="1990-05-15",
            birth_time="12:00",
            language=Language.EN,
        )

        with patch("temporalio.activity.logger"):
            result_no_time = await calculate_saju(user_no_time)
            result_noon = await calculate_saju(user_noon)

        # Should be the same since default is noon
        assert result_no_time.hour_pillar == result_noon.hour_pillar

    @pytest.mark.asyncio
    async def test_known_date_2024_dragon(self):
        """2024 is the Year of the Dragon (辰/진)."""
        from unittest.mock import patch

        user = UserInput(
            name="Dragon",
            birth_date="2024-01-15",
            language=Language.KO,
        )

        with patch("temporalio.activity.logger"):
            result = await calculate_saju(user)

        # 2024: stem=0 (갑/甲), branch=4 (진/辰 Dragon)
        assert "갑(甲)" in result.year_pillar
        assert "진(辰)" in result.year_pillar

    @pytest.mark.asyncio
    async def test_known_date_2024_dragon_english(self):
        """2024 Year of the Dragon in English."""
        from unittest.mock import patch

        user = UserInput(
            name="Dragon",
            birth_date="2024-06-01",
            language=Language.EN,
        )

        with patch("temporalio.activity.logger"):
            result = await calculate_saju(user)

        assert "Gap" in result.year_pillar
        assert "Dragon" in result.year_pillar
