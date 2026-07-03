"""Saju (Four Pillars / 사주) calculation activity.

Implements a simplified but culturally authentic Korean Four Pillars astrology
calculation using the Heavenly Stems (천간/天干) and Earthly Branches (지지/地支).
"""

from __future__ import annotations

from datetime import date, datetime

from temporalio import activity

from src.models import Language, SajuResult, UserInput

# ── Heavenly Stems (천간 / 天干) ──────────────────────────────────────────────
HEAVENLY_STEMS_KO = ["갑(甲)", "을(乙)", "병(丙)", "정(丁)", "무(戊)",
                     "기(己)", "경(庚)", "신(辛)", "임(壬)", "계(癸)"]
HEAVENLY_STEMS_EN = ["Gap (Wood+)", "Eul (Wood-)", "Byeong (Fire+)", "Jeong (Fire-)",
                     "Mu (Earth+)", "Gi (Earth-)", "Gyeong (Metal+)", "Sin (Metal-)",
                     "Im (Water+)", "Gye (Water-)"]

# ── Earthly Branches (지지 / 地支) ────────────────────────────────────────────
EARTHLY_BRANCHES_KO = ["자(子)", "축(丑)", "인(寅)", "묘(卯)", "진(辰)", "사(巳)",
                       "오(午)", "미(未)", "신(申)", "유(酉)", "술(戌)", "해(亥)"]
EARTHLY_BRANCHES_EN = ["Ja (Rat)", "Chuk (Ox)", "In (Tiger)", "Myo (Rabbit)",
                       "Jin (Dragon)", "Sa (Snake)", "O (Horse)", "Mi (Sheep)",
                       "Sin (Monkey)", "Yu (Rooster)", "Sul (Dog)", "Hae (Pig)"]

# ── Five Elements mapping (from Heavenly Stem index) ─────────────────────────
ELEMENTS_KO = ["목(木)", "목(木)", "화(火)", "화(火)", "토(土)",
               "토(土)", "금(金)", "금(金)", "수(水)", "수(水)"]
ELEMENTS_EN = ["Wood", "Wood", "Fire", "Fire", "Earth",
               "Earth", "Metal", "Metal", "Water", "Water"]

# ── Month branch mapping (solar month -> branch index) ───────────────────────
# Lunar months roughly correspond: month 1 -> 寅 (index 2), etc.
MONTH_BRANCH_OFFSET = 2  # January maps to index 2 (寅/Tiger)

# ── Hour branch mapping (2-hour blocks starting from 23:00) ──────────────────
HOUR_BRANCHES = [
    (23, 1), (1, 3), (3, 5), (5, 7), (7, 9), (9, 11),
    (11, 13), (13, 15), (15, 17), (17, 19), (19, 21), (21, 23),
]

# ── Interpretations ──────────────────────────────────────────────────────────
ELEMENT_INTERPRETATIONS_KO = {
    "목(木)": "목(木)의 기운을 타고나셨습니다. 성장과 창조의 에너지가 강하며, 새로운 시작을 이끄는 힘이 있습니다. 봄의 나무처럼 유연하면서도 강인한 성격입니다.",
    "화(火)": "화(火)의 기운을 타고나셨습니다. 열정과 활력이 넘치며, 주변을 밝히는 카리스마가 있습니다. 따뜻한 마음으로 사람들을 이끄는 리더의 자질을 가지고 있습니다.",
    "토(土)": "토(土)의 기운을 타고나셨습니다. 안정과 신뢰의 상징으로, 중심을 잡아주는 든든한 존재입니다. 깊은 포용력과 실용적인 지혜를 가지고 있습니다.",
    "금(金)": "금(金)의 기운을 타고나셨습니다. 결단력과 정의감이 강하며, 명확한 판단력을 가지고 있습니다. 가을의 서늘한 바람처럼 냉철하면서도 빛나는 존재입니다.",
    "수(水)": "수(水)의 기운을 타고나셨습니다. 지혜와 적응력이 뛰어나며, 깊은 통찰력을 가지고 있습니다. 물처럼 유연하게 흐르면서도 강한 의지를 품고 있습니다.",
}

ELEMENT_INTERPRETATIONS_EN = {
    "Wood": "You are born with the energy of Wood. You carry the power of growth and creation, with a natural ability to lead new beginnings. Like a tree in spring, you are both flexible and strong.",
    "Fire": "You are born with the energy of Fire. Full of passion and vitality, you have a charisma that lights up those around you. With a warm heart, you possess the qualities of a natural leader.",
    "Earth": "You are born with the energy of Earth. A symbol of stability and trust, you are a solid presence that holds the center. You possess deep embracing power and practical wisdom.",
    "Metal": "You are born with the energy of Metal. Strong in determination and sense of justice, you have clear judgment. Like the cool autumn breeze, you are sharp yet brilliant.",
    "Water": "You are born with the energy of Water. Exceptional in wisdom and adaptability, you have deep insight. Like water, you flow flexibly while holding a strong will within.",
}


def _year_stem_index(year: int) -> int:
    """Heavenly Stem index for a given year (0-9)."""
    return (year - 4) % 10


def _year_branch_index(year: int) -> int:
    """Earthly Branch index for a given year (0-11)."""
    return (year - 4) % 12


def _month_stem_index(year_stem: int, month: int) -> int:
    """Heavenly Stem index for the month.

    Uses the traditional formula: month stem = (year_stem * 2 + month) % 10
    The base offset starts from the Tiger month (month 1 = lunar first month).
    """
    return (year_stem * 2 + month) % 10


def _month_branch_index(month: int) -> int:
    """Earthly Branch index for the month (1-12 -> branch index)."""
    return (month + MONTH_BRANCH_OFFSET - 1) % 12


def _day_stem_branch(d: date) -> tuple[int, int]:
    """Calculate the day's Heavenly Stem and Earthly Branch indices.

    Uses a simplified formula based on the Julian Day Number.
    """
    # Compute a simplified Julian Day Number offset
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    jdn = d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045

    stem = (jdn - 1) % 10
    branch = (jdn - 1) % 12
    return stem, branch


def _hour_branch_index(hour: int) -> int:
    """Earthly Branch index for a given hour (0-23).

    Each branch covers a 2-hour window. 子 (Rat) = 23:00-01:00.
    """
    # Shift so that 23:00 maps to index 0
    return ((hour + 1) % 24) // 2


def _hour_stem_index(day_stem: int, hour_branch: int) -> int:
    """Heavenly Stem index for the hour.

    Formula: hour_stem = (day_stem * 2 + hour_branch) % 10
    """
    return (day_stem * 2 + hour_branch) % 10


def _format_pillar(stem_idx: int, branch_idx: int, lang: Language) -> str:
    """Format a pillar as 'Stem Branch' string."""
    if lang == Language.KO:
        return f"{HEAVENLY_STEMS_KO[stem_idx]} {EARTHLY_BRANCHES_KO[branch_idx]}"
    return f"{HEAVENLY_STEMS_EN[stem_idx]} {EARTHLY_BRANCHES_EN[branch_idx]}"


@activity.defn
async def calculate_saju(input: UserInput) -> SajuResult:
    """Calculate the Four Pillars (사주) from the user's birth information."""
    activity.logger.info(f"Calculating Saju for {input.name}, born {input.birth_date}")

    birth = date.fromisoformat(input.birth_date)
    year = birth.year
    month = birth.month
    lang = input.language

    # ── Year Pillar ──────────────────────────────────────────────────────
    y_stem = _year_stem_index(year)
    y_branch = _year_branch_index(year)

    # ── Month Pillar ─────────────────────────────────────────────────────
    m_stem = _month_stem_index(y_stem, month)
    m_branch = _month_branch_index(month)

    # ── Day Pillar ───────────────────────────────────────────────────────
    d_stem, d_branch = _day_stem_branch(birth)

    # ── Hour Pillar ──────────────────────────────────────────────────────
    if input.birth_time:
        hour = int(input.birth_time.split(":")[0])
    else:
        # Default to noon (午) if no birth time provided
        hour = 12

    h_branch = _hour_branch_index(hour)
    h_stem = _hour_stem_index(d_stem, h_branch)

    # ── Dominant Element (from the Day Stem, which is the "self" in Saju) ─
    element_ko = ELEMENTS_KO[d_stem]
    element_en = ELEMENTS_EN[d_stem]

    if lang == Language.KO:
        element = element_ko
        interpretation = ELEMENT_INTERPRETATIONS_KO[element_ko]
    else:
        element = element_en
        interpretation = ELEMENT_INTERPRETATIONS_EN[element_en]

    return SajuResult(
        year_pillar=_format_pillar(y_stem, y_branch, lang),
        month_pillar=_format_pillar(m_stem, m_branch, lang),
        day_pillar=_format_pillar(d_stem, d_branch, lang),
        hour_pillar=_format_pillar(h_stem, h_branch, lang),
        element=element,
        interpretation=interpretation,
    )
