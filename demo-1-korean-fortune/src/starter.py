"""CLI starter for the Korean Fortune AI Agent workflow.

Usage:
    python -m src.starter --name "홍길동" --birth-date 1990-05-15
    python -m src.starter --name "John" --birth-date 1995-03-22 --mbti ENFP --lang en
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import uuid

from dotenv import load_dotenv

load_dotenv()

from src import get_client
from src.models import FortuneReading, Language, UserInput
from src.workflows.fortune_workflow import FortuneWorkflow

TASK_QUEUE = "korean-fortune-queue"


def slugify_for_id(name: str) -> str:
    """Normalize a name for use in a Temporal workflow ID.

    Lowercases, collapses internal whitespace to hyphens. Non-ASCII (e.g. Korean)
    characters pass through untouched — Temporal accepts them in IDs.
    """
    return re.sub(r"\s+", "-", name.strip().lower())

# ── ANSI color codes ─────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[97m"
BG_BLUE = "\033[44m"


def print_header(user: UserInput) -> None:
    """Print a nice header for the fortune reading."""
    lang = user.language
    if lang == Language.KO:
        title = "한국 운세 AI 에이전트"
        subtitle = "사주 + MBTI + AI 운세 생성"
    else:
        title = "Korean Fortune AI Agent"
        subtitle = "Saju + MBTI + AI Fortune Generation"

    print(f"\n{YELLOW}{'=' * 56}{RESET}")
    print(f"{YELLOW}  {BOLD}{title}{RESET}")
    print(f"{DIM}  {subtitle}{RESET}")
    print(f"{YELLOW}{'=' * 56}{RESET}")
    print(f"  {WHITE}Name:{RESET} {user.name}")
    print(f"  {WHITE}Birth:{RESET} {user.birth_date}" + (f" {user.birth_time}" if user.birth_time else ""))
    if user.mbti:
        print(f"  {WHITE}MBTI:{RESET} {user.mbti}")
    print(f"{YELLOW}{'─' * 56}{RESET}\n")


def print_status(status: str, lang: Language) -> None:
    """Print a workflow status update."""
    status_labels = {
        "initialized": ("초기화 중..." if lang == Language.KO else "Initializing..."),
        "calculating_saju": ("사주 계산 중..." if lang == Language.KO else "Calculating Saju (Four Pillars)..."),
        "analyzing_mbti": ("MBTI 분석 중..." if lang == Language.KO else "Analyzing MBTI..."),
        "generating_fortune": ("AI 운세 생성 중..." if lang == Language.KO else "Generating AI Fortune..."),
        "completed": ("완료!" if lang == Language.KO else "Completed!"),
    }
    label = status_labels.get(status, status)
    icon = "..." if status != "completed" else "OK"
    color = GREEN if status == "completed" else CYAN
    print(f"  {color}[{icon}] {label}{RESET}")


def print_result(fortune: FortuneReading, lang: Language) -> None:
    """Pretty-print the fortune reading result."""
    is_ko = lang == Language.KO
    saju = fortune.saju
    mbti = fortune.mbti

    # ── Saju Section ─────────────────────────────────────────────────────
    section_title = "사주 (四柱) 분석" if is_ko else "Saju (Four Pillars) Analysis"
    print(f"\n{MAGENTA}{BOLD}--- {section_title} ---{RESET}")

    pillar_label = ("연주", "월주", "일주", "시주") if is_ko else ("Year", "Month", "Day", "Hour")
    pillars = [saju.year_pillar, saju.month_pillar, saju.day_pillar, saju.hour_pillar]
    for label, pillar in zip(pillar_label, pillars):
        print(f"  {WHITE}{label}:{RESET} {pillar}")

    elem_label = "오행" if is_ko else "Element"
    print(f"  {WHITE}{elem_label}:{RESET} {YELLOW}{saju.element}{RESET}")
    print(f"\n  {DIM}{saju.interpretation}{RESET}")

    # ── MBTI Section ─────────────────────────────────────────────────────
    section_title = "MBTI 성격 분석" if is_ko else "MBTI Personality Analysis"
    print(f"\n{BLUE}{BOLD}--- {section_title} ---{RESET}")
    print(f"  {WHITE}Type:{RESET} {BOLD}{mbti.mbti_type}{RESET}")
    print(f"  {mbti.description}")

    strengths_label = "강점" if is_ko else "Strengths"
    print(f"  {WHITE}{strengths_label}:{RESET} {', '.join(mbti.strengths)}")
    print(f"  {CYAN}{mbti.compatibility_note}{RESET}")

    # ── Fortune Section ──────────────────────────────────────────────────
    section_title = "오늘의 운세" if is_ko else "Today's Fortune"
    print(f"\n{YELLOW}{BOLD}--- {section_title} ---{RESET}")
    print(f"\n  {WHITE}{fortune.fortune_message}{RESET}")

    advice_label = "조언" if is_ko else "Advice"
    print(f"\n  {GREEN}{BOLD}{advice_label}:{RESET} {GREEN}{fortune.advice}{RESET}")

    # ── Lucky items ──────────────────────────────────────────────────────
    color_label = "행운의 색" if is_ko else "Lucky Color"
    number_label = "행운의 숫자" if is_ko else "Lucky Number"
    print(f"\n  {MAGENTA}{color_label}:{RESET} {fortune.lucky_color}")
    print(f"  {MAGENTA}{number_label}:{RESET} {fortune.lucky_number}")

    print(f"\n{YELLOW}{'=' * 56}{RESET}\n")


async def main() -> None:
    """Parse CLI args, start the workflow, poll status, and print results."""
    parser = argparse.ArgumentParser(
        description="Korean Fortune AI Agent - Start a fortune reading workflow"
    )
    parser.add_argument("--name", type=str, default="홍길동", help="Your name")
    parser.add_argument("--birth-date", type=str, default="1990-05-15", help="Birth date (YYYY-MM-DD)")
    parser.add_argument("--birth-time", type=str, default=None, help="Birth time (HH:MM, 24h format)")
    parser.add_argument("--mbti", type=str, default=None, help="Your MBTI type (e.g. INFP)")
    parser.add_argument("--lang", type=str, default="ko", choices=["ko", "en"], help="Language (ko/en)")

    args = parser.parse_args()

    user_input = UserInput(
        name=args.name,
        birth_date=args.birth_date,
        birth_time=args.birth_time,
        mbti=args.mbti.upper() if args.mbti else None,
        language=Language(args.lang),
    )

    print_header(user_input)

    # Connect to Temporal
    print(f"  {DIM}Connecting to Temporal...{RESET}")
    client = await get_client()

    # Start the workflow
    workflow_id = f"fortune-{slugify_for_id(user_input.name)}-{uuid.uuid4().hex[:8]}"
    print(f"  {DIM}Starting workflow: {workflow_id}{RESET}\n")

    handle = await client.start_workflow(
        FortuneWorkflow.run,
        user_input,
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    # Poll status while waiting
    last_status = ""
    while True:
        try:
            status = await handle.query(FortuneWorkflow.status)
            if status != last_status:
                print_status(status, user_input.language)
                last_status = status
            if status == "completed":
                break
        except Exception:
            pass
        await asyncio.sleep(0.3)

    # Get the result
    result = await handle.result()

    # Parse the result back into our model (Temporal returns dicts)
    if isinstance(result, dict):
        fortune = FortuneReading(**result)
    else:
        fortune = result

    print_result(fortune, user_input.language)


if __name__ == "__main__":
    asyncio.run(main())
