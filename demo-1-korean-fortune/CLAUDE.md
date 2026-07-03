# Demo 1: Korean Fortune / Personality AI Agent

This is **Demo 1** for the Temporal sales event in Korea. It demonstrates how Temporal orchestrates an "agentic AI" workflow that combines Korean cultural elements with modern AI.

## Concept

The workflow blends two cultural phenomena popular in Korea:

- **Saju (사주/四柱)**: Traditional Korean Four Pillars astrology based on birth date/time, using Heavenly Stems (천간) and Earthly Branches (지지)
- **MBTI**: Personality type analysis, which is hugely popular in Korean culture

An AI agent (OpenAI) ties them together into a personalized fortune reading, all orchestrated reliably through Temporal.

## Quick Start

```bash
# 1. Install dependencies
just setup

# 2. Make sure Temporal dev server is running
temporal server start-dev

# 3. Start the worker (in one terminal)
just worker

# 4. Run a fortune reading (in another terminal)
just start --name "홍길동" --birth-date 1990-05-15
just start --name "John" --birth-date 1995-03-22 --mbti ENFP --lang en
```

Set `OPENAI_API_KEY` in a `.env` file (project root) for real LLM-powered fortunes. Without it, the demo uses a mock fortune generator.

## Architecture

```
UserInput
   |
   v
FortuneWorkflow (Temporal Workflow)
   |
   |-- Step 1: calculate_saju    (Activity - deterministic calculation)
   |-- Step 2: analyze_mbti      (Activity - lookup + optional element-based guess)
   |-- Step 3: generate_fortune  (Activity - LLM call via OpenAI SDK)
   |
   v
FortuneReading (result)
```

- **Workflow** (`src/workflows/fortune_workflow.py`): Orchestrates the three steps, exposes status/result queries
- **Activities** (`src/activities/`): Each step is a separate activity with its own timeout
  - `saju.py`: Implements the Four Pillars calculation using Heavenly Stems and Earthly Branches
  - `mbti.py`: MBTI analysis with a fun element-to-MBTI crossover mapping
  - `fortune.py`: LLM call to OpenAI with retry policy for resilience
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
      fortune.py          # AI fortune generation (OpenAI)
    workflows/
      __init__.py
      fortune_workflow.py # Main orchestration workflow
  tests/
    __init__.py
    test_saju.py          # Saju calculation tests
```
