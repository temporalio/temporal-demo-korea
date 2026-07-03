"""Temporal Worker for the Korean Fortune AI Agent.

Registers the FortuneWorkflow and all activities, then runs the worker
on the 'korean-fortune-queue' task queue.
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

load_dotenv()  # load .env from project root

from temporalio.worker import Worker

from src import get_client
from src.activities.fortune import generate_fortune
from src.activities.mbti import analyze_mbti
from src.activities.saju import calculate_saju
from src.workflows.fortune_workflow import FortuneWorkflow
from src.workflows.interactive_workflow import InteractiveFortuneWorkflow

TASK_QUEUE = "korean-fortune-queue"

BANNER = """
\033[93m╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   \033[96m🔮  Korean Fortune AI Agent  /  한국 운세 AI 에이전트  🔮\033[93m   ║
║                                                              ║
║   \033[97mSaju (사주) + MBTI + AI Fortune Generation\033[93m                 ║
║   \033[97mPowered by Temporal + OpenAI\033[93m                               ║
║                                                              ║
║   \033[92mTask Queue: {queue:<45s}\033[93m  ║
║   \033[92mWorkflows:  FortuneWorkflow, InteractiveFortuneWorkflow\033[93m    ║
║   \033[92mActivities: calculate_saju, analyze_mbti, generate_fortune\033[93m ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝\033[0m
"""


async def main() -> None:
    """Start the Temporal worker."""
    print(BANNER.format(queue=TASK_QUEUE))
    print("\033[97mConnecting to Temporal server...\033[0m")

    client = await get_client()

    print("\033[92mConnected! Worker is running. Press Ctrl+C to stop.\033[0m")
    print("\033[90m" + "─" * 60 + "\033[0m")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[FortuneWorkflow, InteractiveFortuneWorkflow],
        activities=[calculate_saju, analyze_mbti, generate_fortune],
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
