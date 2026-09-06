# Demo 1: Korean Fortune / Personality AI Agent

This is **Demo 1** for the Temporal sales event in Korea. It demonstrates how Temporal orchestrates an "agentic AI" workflow that combines Korean cultural elements with modern AI.

## Concept

The workflow blends two cultural phenomena popular in Korea:

- **Saju (사주/四柱)**: Traditional Korean Four Pillars astrology based on birth date/time, using Heavenly Stems (천간) and Earthly Branches (지지)
- **MBTI**: Personality type analysis, which is hugely popular in Korean culture

An AI agent ties them together into a personalized fortune reading, all orchestrated reliably through Temporal. The LLM backend is pluggable (`src/llm.py`): the OpenAI API, or **local-AI mode** using a coding-agent CLI (Claude Code or Cursor) so the demo runs with no API key.

## Quick Start

```bash
# 1. Install dependencies
just setup

# 2. Make sure Temporal dev server is running
temporal server start-dev

# 3. Start the worker (in one terminal)
just worker              # OpenAI API (if OPENAI_API_KEY set)
just worker-local        # local-AI mode via Claude Code CLI (no API key)
just worker-local cursor # local-AI mode via Cursor CLI

# 4. Run a fortune reading (in another terminal)
just start --name "홍길동" --birth-date 1990-05-15
just start --name "John" --birth-date 1995-03-22 --mbti ENFP --lang en
```

Provider selection is env-driven via `FORTUNE_PROVIDER` (`openai` | `claude` | `cursor`). If unset, it uses `openai` when `OPENAI_API_KEY` is present, otherwise defaults to the local `claude` CLI. If the chosen provider is unavailable or errors, the activity falls back to a deterministic mock fortune. See `.env.example` for all knobs (`CLAUDE_CLI_BIN`, `CURSOR_CLI_BIN`, `LOCAL_AI_TIMEOUT`).

## Architecture

```
UserInput
   |
   v
FortuneWorkflow (Temporal Workflow)
   |
   |-- Step 1: calculate_saju    (Activity - deterministic calculation)
   |-- Step 2: analyze_mbti      (Activity - lookup + optional element-based guess)
   |-- Step 3: generate_fortune  (Activity - LLM call via pluggable provider)
   |
   v
FortuneReading (result)
```

- **Workflow** (`src/workflows/fortune_workflow.py`): Orchestrates the three steps, exposes status/result queries
- **Activities** (`src/activities/`): Each step is a separate activity with its own timeout
  - `saju.py`: Implements the Four Pillars calculation using Heavenly Stems and Earthly Branches
  - `mbti.py`: MBTI analysis with a fun element-to-MBTI crossover mapping
  - `fortune.py`: LLM call via the pluggable provider (`src/llm.py`) with retry policy for resilience
- **Models** (`src/models.py`): Pydantic models for all data structures
- **Worker** (`src/worker.py`): Registers workflows and activities on `korean-fortune-queue`
- **Starter** (`src/starter.py`): CLI client with real-time status polling and pretty-printed output

## Key Temporal Selling Points

1. **Reliable AI Agent Orchestration**: Each "agent step" (Saju, MBTI, Fortune) is a Temporal activity with defined timeouts. If any step fails, Temporal handles retries automatically.

2. **LLM Retry Resilience**: The `generate_fortune` activity has a `RetryPolicy(maximum_attempts=3)` and a 60-second timeout, ensuring the workflow survives transient LLM API failures.

3. **Workflow Visibility**: The workflow exposes `status` and `result` queries, allowing real-time monitoring of the agent's progress through the Temporal UI or CLI.

4. **Deterministic Replay**: Pure computation (Saju calculation) is separated from side effects (LLM calls), following Temporal best practices for workflow determinism.

5. **Bilingual Support**: Full Korean and English support demonstrates production-ready internationalization within the workflow.

## File Structure

```
demo-1-korean-fortune/
  pyproject.toml          # Project config and dependencies
  justfile                # Task runner commands
  CLAUDE.md               # This file
  src/
    __init__.py
    models.py             # Pydantic data models
    worker.py             # Temporal worker entry point
    starter.py            # CLI workflow starter
    activities/
      __init__.py
      saju.py             # Saju (Four Pillars) calculation
      mbti.py             # MBTI personality analysis
      fortune.py          # AI fortune generation (pluggable provider)
    llm.py                # LLM provider dispatch: openai / claude / cursor
    workflows/
      __init__.py
      fortune_workflow.py # Main orchestration workflow
  tests/
    __init__.py
    test_saju.py          # Saju calculation tests
```
