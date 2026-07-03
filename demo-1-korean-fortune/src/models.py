"""Data models for the Korean Fortune AI Agent."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Language(str, Enum):
    """Supported languages."""

    KO = "ko"
    EN = "en"


class UserInput(BaseModel):
    """Input from the user for a fortune reading."""

    name: str = Field(description="User's name")
    birth_date: str = Field(
        description="Birth date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    birth_time: str | None = Field(
        default=None,
        description="Birth time in HH:MM format (24h). Optional.",
        pattern=r"^\d{2}:\d{2}$",
    )
    mbti: str | None = Field(
        default=None,
        description="MBTI type, e.g. 'INFP'. Optional.",
        pattern=r"^[IE][NS][TF][JP]$",
    )
    language: Language = Field(
        default=Language.KO,
        description="Preferred language for the reading",
    )


class SajuResult(BaseModel):
    """Result of the Saju (Four Pillars) calculation."""

    year_pillar: str = Field(description="Year pillar (Heavenly Stem + Earthly Branch)")
    month_pillar: str = Field(description="Month pillar")
    day_pillar: str = Field(description="Day pillar")
    hour_pillar: str = Field(description="Hour pillar")
    element: str = Field(description="Dominant element (Wood/Fire/Earth/Metal/Water)")
    interpretation: str = Field(description="Interpretation text in the requested language")


class MBTIAnalysis(BaseModel):
    """MBTI personality analysis result."""

    mbti_type: str = Field(description="MBTI type code, e.g. 'INFP'")
    description: str = Field(description="Description of this personality type")
    strengths: list[str] = Field(description="Key strengths of this type")
    compatibility_note: str = Field(description="Fun compatibility note (Korean MBTI culture)")


class FortuneReading(BaseModel):
    """Complete fortune reading combining Saju + MBTI + AI-generated fortune."""

    saju: SajuResult
    mbti: MBTIAnalysis
    fortune_message: str = Field(description="Personalized fortune message")
    advice: str = Field(description="Actionable advice")
    lucky_color: str = Field(description="Lucky color for today")
    lucky_number: int = Field(description="Lucky number")
