"""MBTI personality analysis activity.

If the user provides their MBTI type, we use it directly.
If not, we make a fun "guess" based on the Saju element -- a uniquely Korean
crossover that blends traditional astrology with modern personality culture.
"""

from __future__ import annotations

from temporalio import activity

from src.models import Language, MBTIAnalysis, UserInput

# ── Element -> MBTI "guess" mapping (fun crossover) ──────────────────────────
# This is a playful mapping, not scientifically rigorous -- but it resonates
# with Korean pop-culture discussions that blend Saju elements with MBTI.
ELEMENT_TO_MBTI: dict[str, str] = {
    # Wood elements
    "목(木)": "ENFP",
    "Wood": "ENFP",
    # Fire elements
    "화(火)": "ENTJ",
    "Fire": "ENTJ",
    # Earth elements
    "토(土)": "ISFJ",
    "Earth": "ISFJ",
    # Metal elements
    "금(金)": "ISTJ",
    "Metal": "ISTJ",
    # Water elements
    "수(水)": "INFJ",
    "Water": "INFJ",
}

# ── MBTI descriptions ────────────────────────────────────────────────────────
MBTI_DATA_KO: dict[str, dict] = {
    "INTJ": {
        "description": "전략가 - 상상력이 풍부하고 전략적인 사고를 하는 유형입니다. 모든 것에 대한 계획을 가지고 있습니다.",
        "strengths": ["전략적 사고", "독립적", "결단력", "높은 자기 기준", "지적 호기심"],
        "compatibility": "ENFP와의 궁합이 좋습니다! 서로의 부족한 부분을 채워주는 환상의 조합이에요.",
    },
    "INTP": {
        "description": "논리술사 - 끊임없이 지식을 추구하는 혁신적인 발명가 유형입니다.",
        "strengths": ["분석적 사고", "독창성", "객관성", "논리적", "호기심"],
        "compatibility": "ENTJ와 찰떡궁합! 아이디어를 현실로 만들어주는 최고의 파트너입니다.",
    },
    "ENTJ": {
        "description": "통솔자 - 대담하고 상상력이 풍부한 강한 의지의 리더 유형입니다.",
        "strengths": ["리더십", "자신감", "효율성", "전략적 사고", "결단력"],
        "compatibility": "INFP와 의외의 케미! 부드러운 감성이 강한 리더십에 균형을 맞춰줍니다.",
    },
    "ENTP": {
        "description": "변론가 - 도전을 즐기는 똑똑한 호기심쟁이 유형입니다.",
        "strengths": ["창의력", "지적 능력", "카리스마", "에너지", "자신감"],
        "compatibility": "INFJ와 최고의 궁합! 깊은 대화를 나눌 수 있는 소울메이트에요.",
    },
    "INFJ": {
        "description": "옹호자 - 조용하고 신비로우며, 영감을 주는 이상주의자 유형입니다.",
        "strengths": ["통찰력", "원칙적", "열정적", "이타적", "창의적"],
        "compatibility": "ENTP와 환상의 조합! 서로의 세계를 넓혀주는 관계입니다.",
    },
    "INFP": {
        "description": "중재자 - 항상 선한 면을 찾으려 하는 시적이고 친절한 이타주의자입니다.",
        "strengths": ["공감능력", "창의력", "열린 마음", "열정", "이상주의"],
        "compatibility": "ENFJ와 베스트 매치! 서로의 가치를 존중하는 따뜻한 관계를 만들어요.",
    },
    "ENFJ": {
        "description": "주인공 - 카리스마 있고 영감을 주는 리더, 사람들을 매료시키는 유형입니다.",
        "strengths": ["카리스마", "공감능력", "리더십", "신뢰감", "이타적"],
        "compatibility": "INFP와 찰떡궁합! 감성과 따뜻함을 나누는 아름다운 관계입니다.",
    },
    "ENFP": {
        "description": "활동가 - 열정적이고 창의적인 자유로운 영혼, 항상 웃을 이유를 찾는 유형입니다.",
        "strengths": ["열정", "창의력", "사교성", "낙관적", "유연성"],
        "compatibility": "INTJ와 의외의 궁합! 깊이와 에너지가 만나 최고의 시너지를 냅니다.",
    },
    "ISTJ": {
        "description": "현실주의자 - 사실에 근거한 신뢰할 수 있는 유형, 책임감의 아이콘입니다.",
        "strengths": ["책임감", "신뢰성", "인내력", "정직", "체계적"],
        "compatibility": "ESFP와 좋은 궁합! 안정감과 활력이 만나 균형 잡힌 관계를 만듭니다.",
    },
    "ISFJ": {
        "description": "수호자 - 매우 헌신적이고 따뜻한 보호자, 사랑하는 사람을 지키는 유형입니다.",
        "strengths": ["헌신적", "관찰력", "인내력", "신뢰성", "따뜻함"],
        "compatibility": "ESFP 또는 ESTP와 좋은 궁합! 에너지와 안정감의 완벽한 조화에요.",
    },
    "ESTJ": {
        "description": "경영자 - 사물과 사람을 관리하는 뛰어난 능력을 가진 유형입니다.",
        "strengths": ["조직력", "리더십", "헌신", "정직", "인내력"],
        "compatibility": "ISTP와 실용적인 궁합! 함께 목표를 달성하는 파워 커플이에요.",
    },
    "ESFJ": {
        "description": "집정관 - 배려심이 넘치고 사교적인 유형, 주변 사람들을 돕는 것을 좋아합니다.",
        "strengths": ["배려심", "사교성", "충성심", "협동심", "실용적"],
        "compatibility": "ISFP와 따뜻한 궁합! 서로를 돌보는 아름다운 관계입니다.",
    },
    "ISTP": {
        "description": "장인 - 대담하고 실용적인 실험가, 모든 종류의 도구를 다루는 데 능합니다.",
        "strengths": ["적응력", "관찰력", "논리적", "실용적", "위기 대처 능력"],
        "compatibility": "ESTJ와 효율적인 궁합! 실용적이고 생산적인 관계를 만들어요.",
    },
    "ISFP": {
        "description": "모험가 - 유연하고 매력적인 예술가, 항상 새로운 것을 탐험하려는 유형입니다.",
        "strengths": ["예술적 감각", "매력", "탐험 정신", "유연성", "열정"],
        "compatibility": "ESFJ 또는 ENFJ와 좋은 궁합! 따뜻한 배려를 주고받는 관계에요.",
    },
    "ESTP": {
        "description": "사업가 - 에너지 넘치고 관찰력이 뛰어난 유형, 위험을 즐기는 도전가입니다.",
        "strengths": ["에너지", "관찰력", "직접적", "사교적", "대담함"],
        "compatibility": "ISFJ와 균형 잡힌 궁합! 모험과 안정이 만나는 흥미로운 관계입니다.",
    },
    "ESFP": {
        "description": "연예인 - 자발적이고 에너지 넘치는 엔터테이너, 주변을 즐겁게 하는 유형입니다.",
        "strengths": ["에너지", "유머 감각", "사교성", "관찰력", "실용적"],
        "compatibility": "ISTJ와 의외의 궁합! 재미와 안정의 완벽한 밸런스에요.",
    },
}

MBTI_DATA_EN: dict[str, dict] = {
    "INTJ": {
        "description": "The Architect - Imaginative and strategic thinkers with a plan for everything.",
        "strengths": ["Strategic thinking", "Independent", "Decisive", "High standards", "Intellectual curiosity"],
        "compatibility": "Great match with ENFP! They complement each other's weaknesses perfectly.",
    },
    "INTP": {
        "description": "The Logician - Innovative inventors with an unquenchable thirst for knowledge.",
        "strengths": ["Analytical", "Original", "Objective", "Logical", "Curious"],
        "compatibility": "Perfect match with ENTJ! The best partner to turn ideas into reality.",
    },
    "ENTJ": {
        "description": "The Commander - Bold, imaginative, and strong-willed leaders.",
        "strengths": ["Leadership", "Confidence", "Efficiency", "Strategic vision", "Decisiveness"],
        "compatibility": "Surprising chemistry with INFP! Gentle sensitivity balances strong leadership.",
    },
    "ENTP": {
        "description": "The Debater - Smart and curious thinkers who love intellectual challenges.",
        "strengths": ["Creativity", "Intellect", "Charisma", "Energy", "Confidence"],
        "compatibility": "Best match with INFJ! Soulmates who can share deep conversations.",
    },
    "INFJ": {
        "description": "The Advocate - Quiet and mystical, yet very inspiring and tireless idealists.",
        "strengths": ["Insightful", "Principled", "Passionate", "Altruistic", "Creative"],
        "compatibility": "Dream team with ENTP! A relationship that expands each other's worlds.",
    },
    "INFP": {
        "description": "The Mediator - Poetic, kind, and altruistic, always looking for the good in people.",
        "strengths": ["Empathy", "Creativity", "Open-mindedness", "Passion", "Idealism"],
        "compatibility": "Best match with ENFJ! A warm relationship built on mutual respect.",
    },
    "ENFJ": {
        "description": "The Protagonist - Charismatic and inspiring leaders who captivate people.",
        "strengths": ["Charisma", "Empathy", "Leadership", "Reliability", "Altruism"],
        "compatibility": "Perfect match with INFP! A beautiful relationship of shared warmth.",
    },
    "ENFP": {
        "description": "The Campaigner - Enthusiastic, creative free spirits who always find a reason to smile.",
        "strengths": ["Enthusiasm", "Creativity", "Sociability", "Optimism", "Flexibility"],
        "compatibility": "Surprising match with INTJ! Depth meets energy for amazing synergy.",
    },
    "ISTJ": {
        "description": "The Logistician - Practical and fact-minded, the icon of reliability and duty.",
        "strengths": ["Responsibility", "Reliability", "Patience", "Honesty", "Methodical"],
        "compatibility": "Great match with ESFP! Stability meets vitality for a balanced relationship.",
    },
    "ISFJ": {
        "description": "The Defender - Very dedicated and warm protectors, always ready to defend loved ones.",
        "strengths": ["Dedication", "Observant", "Patient", "Reliable", "Warmth"],
        "compatibility": "Great match with ESFP or ESTP! A perfect harmony of energy and stability.",
    },
    "ESTJ": {
        "description": "The Executive - Excellent administrators with an outstanding ability to manage things and people.",
        "strengths": ["Organization", "Leadership", "Dedication", "Honesty", "Patience"],
        "compatibility": "Practical match with ISTP! A power couple that achieves goals together.",
    },
    "ESFJ": {
        "description": "The Consul - Extraordinarily caring and social, always eager to help those around them.",
        "strengths": ["Caring", "Sociability", "Loyalty", "Cooperation", "Practical"],
        "compatibility": "Warm match with ISFP! A beautiful relationship of mutual care.",
    },
    "ISTP": {
        "description": "The Virtuoso - Bold and practical experimenters, masters of all kinds of tools.",
        "strengths": ["Adaptability", "Observant", "Logical", "Practical", "Crisis management"],
        "compatibility": "Efficient match with ESTJ! A practical and productive relationship.",
    },
    "ISFP": {
        "description": "The Adventurer - Flexible and charming artists, always ready to explore something new.",
        "strengths": ["Artistic sense", "Charm", "Exploration", "Flexibility", "Passion"],
        "compatibility": "Great match with ESFJ or ENFJ! A relationship of warm mutual care.",
    },
    "ESTP": {
        "description": "The Entrepreneur - Energetic and perceptive, enjoying living on the edge.",
        "strengths": ["Energy", "Perceptive", "Direct", "Sociable", "Bold"],
        "compatibility": "Balanced match with ISFJ! Adventure meets stability in an exciting way.",
    },
    "ESFP": {
        "description": "The Entertainer - Spontaneous, energetic entertainers who light up the room.",
        "strengths": ["Energy", "Humor", "Sociability", "Observant", "Practical"],
        "compatibility": "Surprising match with ISTJ! The perfect balance of fun and stability.",
    },
}


@activity.defn
async def analyze_mbti(input: UserInput) -> MBTIAnalysis:
    """Analyze the user's MBTI type or guess one from their Saju element."""
    activity.logger.info(f"Analyzing MBTI for {input.name}")

    mbti_type = input.mbti

    if not mbti_type:
        # Fun Korean-style crossover: guess MBTI from Saju element
        # We need to compute element from birth date (same logic as saju activity)
        from src.activities.saju import _day_stem_branch, ELEMENTS_EN
        from datetime import date

        birth = date.fromisoformat(input.birth_date)
        d_stem, _ = _day_stem_branch(birth)
        element_en = ELEMENTS_EN[d_stem]
        mbti_type = ELEMENT_TO_MBTI.get(element_en, "INFP")
        activity.logger.info(f"No MBTI provided; guessed {mbti_type} from element {element_en}")

    mbti_type = mbti_type.upper()

    if input.language == Language.KO:
        data = MBTI_DATA_KO.get(mbti_type, MBTI_DATA_KO["INFP"])
    else:
        data = MBTI_DATA_EN.get(mbti_type, MBTI_DATA_EN["INFP"])

    return MBTIAnalysis(
        mbti_type=mbti_type,
        description=data["description"],
        strengths=data["strengths"],
        compatibility_note=data["compatibility"],
    )
