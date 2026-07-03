"""Fortune generation activity using OpenAI.

This activity combines Saju and MBTI results and uses an LLM to generate
a personalized fortune reading. If the OPENAI_API_KEY is not set, it
falls back to a mock fortune for demo purposes.
"""

from __future__ import annotations

import json
import os
import random

from temporalio import activity

from src.models import (
    FortuneReading,
    Language,
    MBTIAnalysis,
    SajuResult,
    UserInput,
)

LUCKY_COLORS_KO = ["빨강", "파랑", "초록", "보라", "금색", "은색", "하늘색", "분홍", "노랑", "주황"]
LUCKY_COLORS_EN = ["Red", "Blue", "Green", "Purple", "Gold", "Silver", "Sky Blue", "Pink", "Yellow", "Orange"]


def _build_prompt(saju: SajuResult, mbti: MBTIAnalysis, user: UserInput) -> str:
    """Build a rich prompt combining Saju and MBTI data."""
    if user.language == Language.KO:
        return f"""당신은 한국 전통 사주(四柱)와 현대 MBTI 성격 분석을 결합한 전문 운세 상담사입니다.

다음 사용자의 정보를 바탕으로 개인 맞춤 운세를 작성해 주세요.

사용자 이름: {user.name}
생년월일: {user.birth_date}

사주 분석 결과:
- 연주(年柱): {saju.year_pillar}
- 월주(月柱): {saju.month_pillar}
- 일주(日柱): {saju.day_pillar}
- 시주(時柱): {saju.hour_pillar}
- 오행: {saju.element}
- 해석: {saju.interpretation}

MBTI 분석 결과:
- 유형: {mbti.mbti_type}
- 설명: {mbti.description}
- 강점: {', '.join(mbti.strengths)}
- 궁합: {mbti.compatibility_note}

다음 JSON 형식으로 응답해 주세요 (JSON만 출력, 다른 텍스트 없이):
{{
    "fortune_message": "사주와 MBTI를 결합한 깊이 있는 운세 메시지 (3-4문장)",
    "advice": "오늘 하루를 위한 구체적인 조언 (2-3문장)",
    "lucky_color": "행운의 색깔 (한국어)",
    "lucky_number": 행운의 숫자 (1-99 사이 정수)
}}"""
    else:
        return f"""You are an expert fortune counselor who combines traditional Korean Saju (Four Pillars astrology) with modern MBTI personality analysis.

Create a personalized fortune reading based on the following user information.

User name: {user.name}
Birth date: {user.birth_date}

Saju (Four Pillars) Analysis:
- Year Pillar: {saju.year_pillar}
- Month Pillar: {saju.month_pillar}
- Day Pillar: {saju.day_pillar}
- Hour Pillar: {saju.hour_pillar}
- Element: {saju.element}
- Interpretation: {saju.interpretation}

MBTI Analysis:
- Type: {mbti.mbti_type}
- Description: {mbti.description}
- Strengths: {', '.join(mbti.strengths)}
- Compatibility: {mbti.compatibility_note}

Respond in the following JSON format ONLY (no other text):
{{
    "fortune_message": "A deep fortune message combining Saju and MBTI insights (3-4 sentences)",
    "advice": "Specific actionable advice for today (2-3 sentences)",
    "lucky_color": "Lucky color in English",
    "lucky_number": a lucky number between 1 and 99 (integer)
}}"""


def _generate_mock_fortune(
    saju: SajuResult, mbti: MBTIAnalysis, user: UserInput
) -> FortuneReading:
    """Generate a mock fortune when no API key is available."""
    activity.logger.warning("OPENAI_API_KEY not set; generating mock fortune for demo")

    is_ko = user.language == Language.KO
    lucky_number = random.randint(1, 99)

    if is_ko:
        lucky_color = random.choice(LUCKY_COLORS_KO)
        fortune_message = (
            f"{user.name}님, {saju.element}의 기운과 {mbti.mbti_type}의 성격이 만나 "
            f"오늘 특별한 에너지가 흐릅니다. "
            f"사주의 {saju.year_pillar} 연주가 보여주듯, 큰 흐름 속에서 당신만의 빛을 발할 시기입니다. "
            f"{mbti.mbti_type}의 강점인 {mbti.strengths[0]}이(가) 오늘 특히 빛날 것입니다."
        )
        advice = (
            f"오늘은 {mbti.strengths[0]}을(를) 발휘할 수 있는 기회를 찾아보세요. "
            f"{saju.element}의 에너지와 조화를 이루면 좋은 결과가 있을 것입니다. "
            f"점심 시간에 잠시 자연과 함께하는 시간을 가져보세요."
        )
    else:
        lucky_color = random.choice(LUCKY_COLORS_EN)
        fortune_message = (
            f"{user.name}, the energy of {saju.element} meets the {mbti.mbti_type} personality "
            f"to create a special flow of energy today. "
            f"As your Year Pillar ({saju.year_pillar}) suggests, this is a time to shine in the greater flow. "
            f"Your {mbti.mbti_type} strength of {mbti.strengths[0]} will be especially powerful today."
        )
        advice = (
            f"Today, look for opportunities to leverage your {mbti.strengths[0]}. "
            f"Harmonize with your {saju.element} energy for the best results. "
            f"Take a moment during lunch to connect with nature."
        )

    return FortuneReading(
        saju=saju,
        mbti=mbti,
        fortune_message=fortune_message,
        advice=advice,
        lucky_color=lucky_color,
        lucky_number=lucky_number,
    )


@activity.defn
async def generate_fortune(
    saju: SajuResult, mbti: MBTIAnalysis, user: UserInput
) -> FortuneReading:
    """Generate a personalized fortune reading using OpenAI.

    Falls back to a mock fortune if OPENAI_API_KEY is not set.
    """
    activity.logger.info(f"Generating fortune for {user.name}")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _generate_mock_fortune(saju, mbti, user)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = _build_prompt(saju, mbti, user)

    try:
        response = client.chat.completions.create(
            model="gpt-5.5",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.8,
        )

        response_text = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        data = json.loads(response_text)

        return FortuneReading(
            saju=saju,
            mbti=mbti,
            fortune_message=data["fortune_message"],
            advice=data["advice"],
            lucky_color=data["lucky_color"],
            lucky_number=int(data["lucky_number"]),
        )

    except Exception as e:
        activity.logger.error(f"LLM call failed: {e}. Falling back to mock fortune.")
        return _generate_mock_fortune(saju, mbti, user)
