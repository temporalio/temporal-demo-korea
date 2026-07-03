"""Fortune Workflow -- orchestrates the Saju, MBTI, and AI fortune activities.

This workflow demonstrates Temporal's agentic AI orchestration:
  1. Calculate Saju (Four Pillars) from birth data
  2. Analyze MBTI personality
  3. Generate a personalized fortune via LLM (with retries)

Each step is a Temporal activity with its own timeout and retry policy,
ensuring reliability even when LLM calls are flaky.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.activities.fortune import generate_fortune
    from src.activities.mbti import analyze_mbti
    from src.activities.saju import calculate_saju
    from src.models import FortuneReading, UserInput


@workflow.defn
class FortuneWorkflow:
    """Agentic AI workflow that combines Saju + MBTI + LLM fortune generation."""

    def __init__(self) -> None:
        self._status: str = "initialized"
        self._result: Optional[FortuneReading] = None

    @workflow.run
    async def run(self, input: UserInput) -> FortuneReading:
        workflow.logger.info(f"Starting fortune reading for {input.name}")

        # ── Step 1: Calculate Saju (Four Pillars) ────────────────────────
        self._status = "calculating_saju"
        saju = await workflow.execute_activity(
            calculate_saju,
            input,
            start_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info(f"Saju calculated: element={saju.element}")

        # ── Step 2: Analyze MBTI ─────────────────────────────────────────
        self._status = "analyzing_mbti"
        mbti = await workflow.execute_activity(
            analyze_mbti,
            input,
            start_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info(f"MBTI analyzed: type={mbti.mbti_type}")

        # ── Step 3: Generate Fortune (LLM call) ─────────────────────────
        # Longer timeout and retries because LLM calls can be flaky
        self._status = "generating_fortune"
        fortune = await workflow.execute_activity(
            generate_fortune,
            args=[saju, mbti, input],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        workflow.logger.info("Fortune generated successfully")

        self._status = "completed"
        self._result = fortune
        return fortune

    @workflow.query
    def status(self) -> str:
        """Query the current workflow status."""
        return self._status

    @workflow.query
    def result(self) -> Optional[FortuneReading]:
        """Query the workflow result (available after completion)."""
        return self._result
