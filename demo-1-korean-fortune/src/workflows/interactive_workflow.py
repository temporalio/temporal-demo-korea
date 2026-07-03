"""Interactive Fortune Workflow -- infinite loop with step-by-step input via updates.

Demonstrates Temporal's workflow.update handler for request-response interaction.
The workflow runs forever, collecting user info step-by-step (like a CLI wizard),
generating a fortune reading, and then looping back for the next person.

Also demonstrates workflow.upsert_memo() to record each step's input as searchable
metadata visible in the Temporal UI.

Steps: language -> name -> birth_date -> birth_time -> gender -> mbti -> [generate fortune]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.activities.fortune import generate_fortune
    from src.activities.mbti import analyze_mbti
    from src.activities.saju import calculate_saju
    from src.models import FortuneReading, Language, UserInput


# The ordered steps the wizard walks through
STEPS = ["language", "name", "birth_date", "birth_time", "gender", "mbti"]

# Prompts for each step (bilingual). Language prompt is ALWAYS shown in both
# languages -- we don't know which one the user prefers yet, and on session
# repeats the previously-selected language shouldn't bias the next person.
LANGUAGE_PROMPT_BILINGUAL = (
    "언어를 선택하세요 / Choose your language (ko/en) "
    "['exit'로 종료 / type 'exit' to quit]"
)

PROMPTS = {
    "language": {
        "ko": LANGUAGE_PROMPT_BILINGUAL,
        "en": LANGUAGE_PROMPT_BILINGUAL,
    },
    "name": {
        "ko": "이름을 입력하세요 ['exit'로 종료]",
        "en": "Enter your name [type 'exit' to quit]",
    },
    "birth_date": {
        "ko": "생년월일을 입력하세요 (YYYY-MM-DD) ['exit'로 종료]",
        "en": "Enter your birth date (YYYY-MM-DD) [type 'exit' to quit]",
    },
    "birth_time": {
        "ko": "태어난 시간을 입력하세요 (HH:MM, 24시간제) [Enter로 건너뛰기 / 'exit'로 종료]",
        "en": "Enter your birth time (HH:MM, 24h) [Enter to skip / 'exit' to quit]",
    },
    "gender": {
        "ko": "성별을 입력하세요 (M/F/O) [Enter로 건너뛰기 / 'exit'로 종료]",
        "en": "Enter your gender (M/F/O) [Enter to skip / 'exit' to quit]",
    },
    "mbti": {
        "ko": "MBTI를 입력하세요 (예: INFP) [Enter로 건너뛰기 - 사주로 추측합니다! / 'exit'로 종료]",
        "en": "Enter your MBTI (e.g. INFP) [Enter to skip - we'll guess from Saju! / 'exit' to quit]",
    },
}


@dataclass
class StepPrompt:
    """Returned to the client so it knows what to ask next."""
    step: str
    prompt: str
    session_number: int
    is_complete: bool = False
    is_exiting: bool = False
    fortune: Optional[dict] = None
    error: Optional[str] = None


@workflow.defn
class InteractiveFortuneWorkflow:
    """Infinite-loop workflow that collects user input step-by-step via updates.

    The client sends input one field at a time using execute_update().
    After all fields are collected, the workflow runs the fortune pipeline,
    returns the result, and resets for the next person.

    Type 'exit' at any step to shut down the workflow entirely.

    Each step's input is recorded as a Temporal memo for visibility in the UI.
    """

    def __init__(self) -> None:
        self._current_step_idx: int = 0
        self._session_number: int = 1
        self._language: str = "ko"
        self._fields: dict[str, str] = {}
        self._shutdown: bool = False
        self._fortune_result: Optional[FortuneReading] = None
        self._generating: bool = False

    @workflow.run
    async def run(self) -> None:
        """Run forever, waiting for updates. Only exits on shutdown signal or 'exit' command."""
        workflow.logger.info("Interactive Fortune Workflow started. Waiting for input...")
        workflow.upsert_memo({"status": "waiting_for_input", "session": self._session_number})
        await workflow.wait_condition(lambda: self._shutdown)
        workflow.upsert_memo({"status": "shutdown"})
        workflow.logger.info("Interactive Fortune Workflow shutting down.")

    @workflow.update
    async def submit_input(self, value: str) -> StepPrompt:
        """Accept one step of user input. Returns the next prompt or the fortune result.

        If the user types 'exit', the workflow shuts down gracefully.
        """

        # Handle exit command at any step
        if value.strip().lower() == "exit":
            workflow.logger.info("User requested exit.")
            workflow.upsert_memo({
                "status": "exiting",
                "exit_at_step": STEPS[self._current_step_idx] if self._current_step_idx < len(STEPS) else "done",
                "exit_at_session": self._session_number,
            })
            self._shutdown = True
            return StepPrompt(
                step="exit",
                prompt="",
                session_number=self._session_number,
                is_exiting=True,
            )

        # If we just finished a fortune, this call starts a new session
        if self._fortune_result is not None:
            self._reset_session()

        step = STEPS[self._current_step_idx]

        # Validate and store the input
        error = self._validate(step, value)
        if error:
            return StepPrompt(
                step=step,
                prompt=PROMPTS[step][self._language],
                session_number=self._session_number,
                error=error,
            )

        self._store(step, value)
        self._current_step_idx += 1

        # Record step in memo
        self._upsert_step_memo(step, value)

        # If we've collected all fields, generate the fortune
        if self._current_step_idx >= len(STEPS):
            return await self._generate_fortune()

        # Otherwise, return the next prompt
        next_step = STEPS[self._current_step_idx]
        return StepPrompt(
            step=next_step,
            prompt=PROMPTS[next_step][self._language],
            session_number=self._session_number,
        )

    @workflow.query
    def current_prompt(self) -> StepPrompt:
        """Query the current step prompt (useful for reconnecting clients)."""
        if self._fortune_result is not None:
            return StepPrompt(
                step="done",
                prompt="",
                session_number=self._session_number,
                is_complete=True,
                fortune=self._fortune_result.model_dump(),
            )
        if self._generating:
            return StepPrompt(
                step="generating",
                prompt="Generating fortune..." if self._language == "en" else "운세 생성 중...",
                session_number=self._session_number,
            )
        step = STEPS[self._current_step_idx]
        return StepPrompt(
            step=step,
            prompt=PROMPTS[step][self._language],
            session_number=self._session_number,
        )

    @workflow.query
    def session_number(self) -> int:
        """Return the current session number."""
        return self._session_number

    @workflow.signal
    async def shutdown(self) -> None:
        """Signal the workflow to exit its infinite loop."""
        self._shutdown = True

    # ── Internal helpers ─────────────────────────────────────────────

    def _validate(self, step: str, value: str) -> Optional[str]:
        """Validate input for a given step. Returns error message or None."""
        if step == "language":
            if value.lower() not in ("ko", "en"):
                return "잘못된 입력 / Invalid. Choose 'ko' or 'en'."
        elif step == "name":
            if not value.strip():
                return "Name cannot be empty." if self._language == "en" else "이름을 입력해 주세요."
        elif step == "birth_date":
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                return "Format: YYYY-MM-DD" if self._language == "en" else "형식: YYYY-MM-DD"
        elif step == "birth_time":
            import re
            if value.strip() and not re.match(r"^\d{2}:\d{2}$", value):
                return "Format: HH:MM (24h)" if self._language == "en" else "형식: HH:MM (24시간제)"
        elif step == "gender":
            if value.strip() and value.upper() not in ("M", "F", "O"):
                return "Choose M, F, or O." if self._language == "en" else "M, F, O 중 선택하세요."
        elif step == "mbti":
            import re
            if value.strip() and not re.match(r"^[IiEe][NnSs][TtFf][JjPp]$", value):
                return "Format: e.g. INFP" if self._language == "en" else "형식: 예) INFP"
        return None

    def _store(self, step: str, value: str) -> None:
        """Store validated input."""
        if step == "language":
            self._language = value.lower()
        else:
            self._fields[step] = value.strip()

    def _upsert_step_memo(self, step: str, value: str) -> None:
        """Record the step's input in workflow memo for Temporal UI visibility."""
        memo_key = f"session_{self._session_number}"
        # Build the current session's collected data so far
        session_data: dict = {
            "language": self._language,
            **{k: v for k, v in self._fields.items() if v},
        }
        workflow.upsert_memo({
            "status": f"collecting_input:{step}",
            "session": self._session_number,
            "current_step": STEPS[self._current_step_idx] if self._current_step_idx < len(STEPS) else "done",
            memo_key: session_data,
        })

    def _reset_session(self) -> None:
        """Reset for a new person."""
        self._current_step_idx = 0
        self._fields = {}
        self._fortune_result = None
        self._generating = False
        self._session_number += 1
        workflow.upsert_memo({
            "status": "waiting_for_input",
            "session": self._session_number,
            "current_step": "language",
        })

    async def _generate_fortune(self) -> StepPrompt:
        """Run the fortune pipeline and return the result."""
        self._generating = True
        workflow.upsert_memo({
            "status": "generating_fortune",
            "session": self._session_number,
        })

        user_input = UserInput(
            name=self._fields["name"],
            birth_date=self._fields["birth_date"],
            birth_time=self._fields.get("birth_time") or None,
            mbti=self._fields["mbti"].upper() if self._fields.get("mbti") else None,
            language=Language(self._language),
        )

        # Step 1: Saju
        saju = await workflow.execute_activity(
            calculate_saju,
            user_input,
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Step 2: MBTI
        mbti = await workflow.execute_activity(
            analyze_mbti,
            user_input,
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Step 3: Fortune (LLM)
        fortune = await workflow.execute_activity(
            generate_fortune,
            args=[saju, mbti, user_input],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        self._generating = False
        self._fortune_result = fortune

        # Record completed fortune in memo
        memo_key = f"session_{self._session_number}"
        session_data: dict = {
            "language": self._language,
            **{k: v for k, v in self._fields.items() if v},
            "fortune_element": fortune.saju.element,
            "fortune_mbti": fortune.mbti.mbti_type,
            "lucky_number": fortune.lucky_number,
        }
        workflow.upsert_memo({
            "status": "fortune_complete",
            "session": self._session_number,
            memo_key: session_data,
        })

        return StepPrompt(
            step="done",
            prompt="",
            session_number=self._session_number,
            is_complete=True,
            fortune=fortune.model_dump(),
        )
