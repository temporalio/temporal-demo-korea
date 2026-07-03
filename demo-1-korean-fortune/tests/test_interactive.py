"""Tests for the InteractiveFortuneWorkflow."""

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

from src.activities.saju import calculate_saju
from src.activities.mbti import analyze_mbti
from src.activities.fortune import generate_fortune
from src.workflows.interactive_workflow import InteractiveFortuneWorkflow, StepPrompt

TASK_QUEUE = "test-interactive-queue"


@pytest.fixture
async def env():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env


@pytest.fixture
async def worker_and_handle(env: WorkflowEnvironment):
    async with Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflows=[InteractiveFortuneWorkflow],
        activities=[calculate_saju, analyze_mbti, generate_fortune],
    ):
        handle = await env.client.start_workflow(
            InteractiveFortuneWorkflow.run,
            id="test-interactive",
            task_queue=TASK_QUEUE,
        )
        yield handle


async def test_step_by_step_collection(worker_and_handle):
    """Walk through all steps and get a fortune reading."""
    handle = worker_and_handle

    # Step 1: language -> returns name prompt
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "en"
    )
    assert result.step == "name"
    assert result.session_number == 1

    # Step 2: name -> returns birth_date prompt
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "John"
    )
    assert result.step == "birth_date"

    # Step 3: birth_date
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "1990-05-15"
    )
    assert result.step == "birth_time"

    # Step 4: birth_time (skip)
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, ""
    )
    assert result.step == "gender"

    # Step 5: gender (skip)
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, ""
    )
    assert result.step == "mbti"

    # Step 6: mbti -> triggers fortune generation
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "INFP"
    )
    assert result.is_complete
    assert result.fortune is not None
    assert result.fortune["mbti"]["mbti_type"] == "INFP"
    assert result.session_number == 1


async def test_validation_error(worker_and_handle):
    """Submitting bad input returns an error and stays on the same step."""
    handle = worker_and_handle

    # Bad language
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "xyz"
    )
    assert result.error is not None
    assert result.step == "language"

    # Now send a valid one
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "ko"
    )
    assert result.step == "name"
    assert result.error is None


async def test_session_loops(worker_and_handle):
    """After completing a fortune, the next input starts a new session."""
    handle = worker_and_handle

    # Complete session 1
    for value in ["en", "Alice", "2000-01-01", "", "", ""]:
        result = await handle.execute_update(
            InteractiveFortuneWorkflow.submit_input, value
        )

    assert result.is_complete
    assert result.session_number == 1

    # Start session 2 -- any input resets and starts from language
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "ko"
    )
    assert result.session_number == 2
    assert result.step == "name"


async def test_query_current_prompt(worker_and_handle):
    """Query returns the current step prompt."""
    handle = worker_and_handle

    prompt = await handle.query(InteractiveFortuneWorkflow.current_prompt)
    assert prompt.step == "language"

    await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "en"
    )

    prompt = await handle.query(InteractiveFortuneWorkflow.current_prompt)
    assert prompt.step == "name"


async def test_exit_at_first_step(worker_and_handle):
    """Typing 'exit' at the first step shuts down the workflow."""
    handle = worker_and_handle

    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "exit"
    )
    assert result.is_exiting
    assert result.step == "exit"

    # Workflow should complete (shutdown triggered)
    await handle.result()


async def test_exit_mid_session(worker_and_handle):
    """Typing 'exit' mid-session shuts down the workflow."""
    handle = worker_and_handle

    # Start a session
    await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "en"
    )
    await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "Alice"
    )

    # Exit at birth_date step
    result = await handle.execute_update(
        InteractiveFortuneWorkflow.submit_input, "exit"
    )
    assert result.is_exiting

    # Workflow should complete
    await handle.result()


async def test_full_session_with_memos(worker_and_handle):
    """Complete a full session -- memos are upserted without error."""
    handle = worker_and_handle

    # Run a full session (memos are upserted at each step internally)
    for value in ["en", "Bob", "1995-06-15", "14:30", "M", "ENFJ"]:
        result = await handle.execute_update(
            InteractiveFortuneWorkflow.submit_input, value
        )

    assert result.is_complete
    assert result.fortune is not None
    assert result.fortune["mbti"]["mbti_type"] == "ENFJ"

    # Verify memo is accessible via describe
    desc = await handle.describe()
    assert desc.memo is not None
