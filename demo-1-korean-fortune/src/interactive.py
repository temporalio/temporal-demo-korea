"""Interactive CLI for the Korean Fortune AI Agent.

A CLI wizard that connects to the InteractiveFortuneWorkflow and walks the user
through input collection step-by-step, like Claude Code's interactive prompts.
The workflow runs forever -- after each fortune reading, it loops back for a new person.

Usage:
    python -m src.interactive
    python -m src.interactive --workflow-id my-booth-session
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from temporalio.client import Client

from src import get_client
from src.models import FortuneReading
from src.workflows.interactive_workflow import InteractiveFortuneWorkflow, StepPrompt

TASK_QUEUE = "korean-fortune-queue"

# ── ANSI ─────────────────────────────────────────────────────────────────────
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


def print_banner() -> None:
    print(f"""
{YELLOW}{'=' * 60}
  {BOLD}Interactive Fortune Booth / 대화형 운세 부스{RESET}
{DIM}  Powered by Temporal Workflow Updates{RESET}
{YELLOW}{'=' * 60}{RESET}
{DIM}  Type your answers step by step. Press Enter to skip optional fields.
  단계별로 답변을 입력하세요. 선택 항목은 Enter로 건너뛸 수 있습니다.
  Type 'exit' at any step to shut down the workflow.
  아무 단계에서 'exit'를 입력하면 워크플로우가 종료됩니다.{RESET}
{YELLOW}{'─' * 60}{RESET}
""")


def print_fortune(fortune_dict: dict, lang: str) -> None:
    """Pretty-print the fortune reading."""
    fortune = FortuneReading(**fortune_dict)
    is_ko = lang == "ko"
    saju = fortune.saju
    mbti = fortune.mbti

    print(f"\n{GREEN}{'=' * 60}{RESET}")
    title = "운세 결과" if is_ko else "Fortune Reading"
    print(f"{GREEN}  {BOLD}{title}{RESET}")
    print(f"{GREEN}{'=' * 60}{RESET}")

    # Saju
    section = "사주 (四柱)" if is_ko else "Saju (Four Pillars)"
    print(f"\n{MAGENTA}{BOLD}  [{section}]{RESET}")
    labels = ("연주", "월주", "일주", "시주") if is_ko else ("Year", "Month", "Day", "Hour")
    for label, pillar in zip(labels, [saju.year_pillar, saju.month_pillar, saju.day_pillar, saju.hour_pillar]):
        print(f"    {WHITE}{label}:{RESET} {pillar}")
    elem_label = "오행" if is_ko else "Element"
    print(f"    {WHITE}{elem_label}:{RESET} {YELLOW}{saju.element}{RESET}")
    print(f"    {DIM}{saju.interpretation}{RESET}")

    # MBTI
    section = "MBTI 분석" if is_ko else "MBTI Analysis"
    print(f"\n{BLUE}{BOLD}  [{section}]{RESET}")
    print(f"    {WHITE}Type:{RESET} {BOLD}{mbti.mbti_type}{RESET}")
    print(f"    {mbti.description}")
    strengths_label = "강점" if is_ko else "Strengths"
    print(f"    {WHITE}{strengths_label}:{RESET} {', '.join(mbti.strengths)}")
    print(f"    {CYAN}{mbti.compatibility_note}{RESET}")

    # Fortune
    section = "오늘의 운세" if is_ko else "Today's Fortune"
    print(f"\n{YELLOW}{BOLD}  [{section}]{RESET}")
    print(f"    {WHITE}{fortune.fortune_message}{RESET}")
    advice_label = "조언" if is_ko else "Advice"
    print(f"\n    {GREEN}{BOLD}{advice_label}:{RESET} {GREEN}{fortune.advice}{RESET}")

    # Lucky items
    color_label = "행운의 색" if is_ko else "Lucky Color"
    number_label = "행운의 숫자" if is_ko else "Lucky Number"
    print(f"\n    {MAGENTA}{color_label}:{RESET} {fortune.lucky_color}")
    print(f"    {MAGENTA}{number_label}:{RESET} {fortune.lucky_number}")

    print(f"\n{GREEN}{'=' * 60}{RESET}")


def print_new_session_banner(session_num: int) -> None:
    print(f"""
{CYAN}{'─' * 60}
  {BOLD}Session #{session_num}{RESET}
{DIM}  New person! Let's start from the beginning.
  새로운 사람! 처음부터 시작합니다.{RESET}
{CYAN}{'─' * 60}{RESET}
""")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Fortune Booth")
    parser.add_argument(
        "--workflow-id",
        default="fortune-booth",
        help="Workflow ID (reuse to reconnect to an existing session)",
    )
    args = parser.parse_args()

    print_banner()

    client = await get_client()

    # Start or connect to the workflow
    workflow_id = args.workflow_id
    try:
        handle = await client.start_workflow(
            InteractiveFortuneWorkflow.run,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )
        print(f"  {DIM}Started workflow: {workflow_id}{RESET}\n")
    except Exception:
        # Workflow already running -- reconnect
        handle = client.get_workflow_handle(workflow_id)
        print(f"  {DIM}Reconnected to workflow: {workflow_id}{RESET}\n")

    # Get the first prompt
    prompt_info: StepPrompt = await handle.query(InteractiveFortuneWorkflow.current_prompt)

    if prompt_info.is_complete:
        # Previous session finished, start fresh by sending any input
        print_new_session_banner(prompt_info.session_number + 1)
        prompt_info = StepPrompt(
            step="language",
            prompt=PROMPTS_FALLBACK["language"],
            session_number=prompt_info.session_number + 1,
        )

    lang = "ko"  # default until language step is answered

    while True:
        step = prompt_info.step
        prompt_text = prompt_info.prompt

        # Show the prompt
        try:
            user_value = input(f"  {CYAN}{BOLD}[{step}]{RESET} {prompt_text}\n  {YELLOW}> {RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n  {DIM}Goodbye! The workflow keeps running on Temporal.{RESET}")
            print(f"  {DIM}Reconnect anytime with: just interactive --workflow-id {workflow_id}{RESET}\n")
            return

        # Send the input via workflow update (request-response)
        try:
            print(f"  {DIM}...{RESET}")
            result: StepPrompt = await handle.execute_update(
                InteractiveFortuneWorkflow.submit_input,
                user_value,
            )
        except Exception as e:
            print(f"  {RED}Error: {e}{RESET}")
            continue

        # Handle exit
        if result.is_exiting:
            exit_msg = "워크플로우가 종료되었습니다." if lang == "ko" else "Workflow has been shut down."
            print(f"\n  {YELLOW}{BOLD}{exit_msg}{RESET}")
            print(f"  {DIM}Workflow ID: {workflow_id}{RESET}\n")
            return

        # Handle validation errors
        if result.error:
            print(f"  {RED}{result.error}{RESET}\n")
            prompt_info = result
            continue

        # Handle completed fortune
        if result.is_complete and result.fortune:
            if result.step == "done" and step == "language":
                # This was the language step for a fresh session after completion
                lang = user_value.lower()
            print_fortune(result.fortune, lang)
            next_hint = (
                "다음 사람을 위해 Enter를 누르세요! ('exit'로 종료)"
                if lang == "ko"
                else "Press Enter for the next person! (type 'exit' to quit)"
            )
            print(f"\n  {CYAN}{BOLD}{next_hint}{RESET}")
            try:
                repeat_value = input(f"  {YELLOW}> {RESET}")
            except (EOFError, KeyboardInterrupt):
                print(f"\n\n  {DIM}Goodbye!{RESET}\n")
                return
            # Honor 'exit' here too -- forward it to the workflow to shut down.
            if repeat_value.strip().lower() == "exit":
                try:
                    await handle.execute_update(
                        InteractiveFortuneWorkflow.submit_input,
                        "exit",
                    )
                except Exception:
                    pass
                exit_msg = "워크플로우가 종료되었습니다." if lang == "ko" else "Workflow has been shut down."
                print(f"\n  {YELLOW}{BOLD}{exit_msg}{RESET}")
                print(f"  {DIM}Workflow ID: {workflow_id}{RESET}\n")
                return
            # New session -- the next submit_input call will trigger reset
            print_new_session_banner(result.session_number + 1)
            prompt_info = StepPrompt(
                step="language",
                prompt=PROMPTS_FALLBACK["language"],
                session_number=result.session_number + 1,
            )
            lang = "ko"
            continue

        # Track language for display
        if step == "language":
            lang = user_value.lower()

        prompt_info = result
        print()


# Fallback prompts (before the workflow responds with the real prompt)
PROMPTS_FALLBACK = {
    "language": (
        "언어를 선택하세요 / Choose your language (ko/en) "
        "['exit'로 종료 / type 'exit' to quit]"
    ),
}


if __name__ == "__main__":
    asyncio.run(main())
