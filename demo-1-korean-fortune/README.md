# Demo 1: Korean Fortune AI Agent / 한국 운세 AI 에이전트

> Temporal + OpenAI (GPT-5.5) | Agentic Workflow | Bilingual (KR/EN)

---

## Overview / 개요

**EN** &mdash; An agentic AI workflow that blends two of Korea's biggest cultural trends &mdash; **Saju (사주, Four Pillars astrology)** and **MBTI** &mdash; with a GPT-5.5-powered fortune generator orchestrated reliably through Temporal.

**KO** &mdash; 한국에서 가장 인기 있는 두 가지 트렌드인 **사주(四柱)**와 **MBTI**를 결합하고, GPT-5.5 기반 AI가 맞춤형 운세를 생성하는 Temporal 워크플로우 데모입니다.

### What does it demonstrate? / 무엇을 보여주나요?

| Temporal Feature | EN | KO |
|---|---|---|
| Activity orchestration | Three-step agentic pipeline (Saju &#8594; MBTI &#8594; LLM Fortune) | 3단계 에이전트 파이프라인 (사주 &#8594; MBTI &#8594; LLM 운세) |
| Retry policy | LLM calls retry automatically on failure (up to 3x) | LLM 호출 실패 시 자동 재시도 (최대 3회) |
| Workflow queries | Poll real-time status while the workflow runs | 워크플로우 실행 중 실시간 상태 조회 |
| Deterministic replay | Pure computation separated from side-effects | 순수 계산과 부수 효과 분리 |

---

## Quick Start / 빠른 시작

### Prerequisites / 사전 준비

- Python 3.11+
- [just](https://just.systems/) (`brew install just`)
- The [Temporal CLI](https://docs.temporal.io/cli) (see below)
- A `.env` file at the project root (copy from `.env.example`)

### 1. Install the Temporal CLI / Temporal CLI 설치

**EN** &mdash; The `temporal` CLI includes a local development server. Install it following the [official guide](https://docs.temporal.io/cli):

**KO** &mdash; `temporal` CLI에는 로컬 개발 서버가 포함되어 있습니다. [공식 가이드](https://docs.temporal.io/cli)를 따라 설치하세요:

```bash
# macOS (Homebrew)
brew install temporal

# macOS / Linux (install script)
curl -sSf https://temporal.download/cli.sh | sh
```

Verify the install / 설치 확인:

```bash
temporal --version
```

### 2. Configure the Temporal connection / Temporal 연결 설정

**EN** &mdash; Copy `.env.example` to `.env` and choose **one** of the two options below. The app reads the connection settings from these environment variables (see `src/__init__.py`), so the same code works against a local server or Temporal Cloud.

**KO** &mdash; `.env.example`를 `.env`로 복사한 뒤 아래 두 가지 중 **하나**를 선택하세요. 앱은 이 환경 변수에서 연결 설정을 읽으므로(`src/__init__.py` 참고), 동일한 코드로 로컬 서버와 Temporal Cloud 모두에 연결할 수 있습니다.

```bash
cp .env.example .env
```

| Variable | Description | EN / KO |
|---|---|---|
| `TEMPORAL_ADDRESS` | Frontend `host:port` | `localhost:7233` for local / 로컬은 `localhost:7233` |
| `TEMPORAL_NAMESPACE` | Namespace | `default` for local / 로컬은 `default` |
| `TEMPORAL_API_KEY` | Cloud API key | Leave empty for local; set for Cloud / 로컬은 비워두고, Cloud는 설정 |

**Option A &mdash; Self-hosted local server (default) / 옵션 A &mdash; 로컬 서버 (기본값)**

Start the local development server in its own terminal / 별도 터미널에서 로컬 개발 서버를 실행하세요:

```bash
temporal server start-dev
```

This launches the server on `localhost:7233` and the Web UI at [http://localhost:8233](http://localhost:8233), and creates the `default` namespace automatically. With `TEMPORAL_API_KEY` left empty, the app connects here over plaintext &mdash; no further config needed.

이 명령은 `localhost:7233`에 서버를, [http://localhost:8233](http://localhost:8233)에 웹 UI를 실행하고 `default` 네임스페이스를 자동으로 생성합니다. `TEMPORAL_API_KEY`를 비워두면 앱이 평문으로 이 서버에 연결합니다.

```dotenv
TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_API_KEY=
```

**Option B &mdash; Temporal Cloud / 옵션 B &mdash; Temporal Cloud**

Set your namespace endpoint and an API key. When `TEMPORAL_API_KEY` is present, the app connects with TLS + API-key authentication automatically.

네임스페이스 엔드포인트와 API 키를 설정하세요. `TEMPORAL_API_KEY`가 있으면 앱이 자동으로 TLS + API 키 인증으로 연결합니다.

```dotenv
TEMPORAL_ADDRESS=<your-namespace>.<account-id>.tmprl.cloud:7233
TEMPORAL_NAMESPACE=<your-namespace>.<account-id>
TEMPORAL_API_KEY=<your-temporal-cloud-api-key>
```

### 3. Setup / 설치

```bash
just setup
```

### Run / 실행

```bash
# Terminal 1: Start the worker / 워커 시작
just worker

# Terminal 2: Run a fortune reading / 운세 실행
just start                                                        # Korean (default / 기본)
just start --name "홍길동" --birth-date 1990-05-15                  # Korean with custom input
just start --name "John" --birth-date 1995-03-22 --mbti ENFP --lang en  # English
```

### Test / 테스트

```bash
just test
```

---

## Architecture / 아키텍처

```
UserInput (name, birth_date, birth_time, mbti, language)
   |
   v
FortuneWorkflow (Temporal Workflow)
   |
   |-- Step 1: calculate_saju    (Activity - 사주 계산 / Four Pillars calculation)
   |      Heavenly Stems (천간) + Earthly Branches (지지)
   |      Dominant element (오행): Wood/Fire/Earth/Metal/Water
   |
   |-- Step 2: analyze_mbti      (Activity - MBTI 분석 / MBTI analysis)
   |      16 personality types, bilingual descriptions
   |      Fun crossover: guess MBTI from Saju element
   |
   |-- Step 3: generate_fortune  (Activity - AI 운세 생성 / LLM fortune generation)
   |      GPT-5.5 via OpenAI SDK
   |      RetryPolicy(maximum_attempts=3), 60s timeout
   |      Graceful fallback to mock if no API key
   |
   v
FortuneReading (fortune_message, advice, lucky_color, lucky_number)
```

---

## File Structure / 파일 구조

```
demo-1-korean-fortune/
  pyproject.toml                # Dependencies: temporalio, openai, pydantic
  justfile                      # setup, worker, start, test
  src/
    __init__.py                 # Temporal Cloud connection helper
    models.py                   # UserInput, SajuResult, MBTIAnalysis, FortuneReading
    worker.py                   # Worker on task queue: korean-fortune-queue
    starter.py                  # CLI with ANSI-colored bilingual output
    activities/
      saju.py                   # 사주 계산 (천간/지지, 60갑자)
      mbti.py                   # MBTI 성격 분석 + 오행-MBTI 매핑
      fortune.py                # GPT-5.5 운세 생성 (mock fallback)
    workflows/
      fortune_workflow.py       # 3-step orchestration with status/result queries
  tests/
    test_saju.py                # 25 unit tests
```

---

## Why Temporal? / 왜 Temporal인가?

**EN**

1. **Reliable AI orchestration** &mdash; Each agent step has defined timeouts and retries. If the LLM call fails, Temporal automatically retries without custom error-handling code.
2. **Visibility** &mdash; Query workflow status in real-time via the Temporal UI, CLI, or SDK. No custom dashboards needed.
3. **Durability** &mdash; Kill the worker mid-workflow, restart it, and the fortune reading picks up exactly where it left off.
4. **Deterministic replay** &mdash; Pure computation (Saju math) is cleanly separated from non-deterministic side-effects (LLM calls), following Temporal best practices.

**KO**

1. **안정적인 AI 오케스트레이션** &mdash; 각 에이전트 단계에 타임아웃과 재시도 정책이 정의되어 있습니다. LLM 호출이 실패해도 별도의 에러 처리 코드 없이 자동으로 재시도합니다.
2. **가시성** &mdash; Temporal UI, CLI 또는 SDK를 통해 워크플로우 상태를 실시간으로 조회할 수 있습니다. 별도 대시보드가 필요 없습니다.
3. **내구성** &mdash; 워커를 워크플로우 중간에 종료하고 다시 시작해도, 운세 생성이 정확히 중단된 지점에서 재개됩니다.
4. **결정론적 리플레이** &mdash; 순수 계산(사주 수학)과 비결정적 부수 효과(LLM 호출)가 깔끔하게 분리되어 Temporal 모범 사례를 따릅니다.
