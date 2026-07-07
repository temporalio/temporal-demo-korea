# Temporal Demos / Temporal 데모

> Two hands-on demos showcasing [Temporal](https://temporal.io/) with the Python SDK
> Temporal Python SDK로 만든 두 가지 실습 데모

---

## Overview / 개요

**EN** &mdash; This repository contains two self-contained demos, each built to highlight different strengths of Temporal &mdash; from durable, retry-safe AI orchestration to the saga pattern with human-in-the-loop approval. Every demo is bilingual (Korean / English) and driven by a [`just`](https://just.systems/) task runner.

**KO** &mdash; 이 저장소에는 Temporal의 다양한 강점을 보여주는 두 가지 독립 실행형 데모가 있습니다. 내구성 있고 재시도에 안전한 AI 오케스트레이션부터 사람의 개입(Human-in-the-Loop) 승인을 포함한 사가 패턴까지 다룹니다. 모든 데모는 이중 언어(한국어/영어)이며 [`just`](https://just.systems/) 태스크 러너로 실행됩니다.

---

## Demos / 데모

### [Demo 1: Korean Fortune AI Agent / 한국 운세 AI 에이전트](./demo-1-korean-fortune)

> Temporal + OpenAI (GPT-5.5) | Agentic Workflow | Bilingual (KR/EN)

**EN** &mdash; An agentic AI workflow that blends two of Korea's biggest cultural trends &mdash; **Saju (사주, Four Pillars astrology)** and **MBTI** &mdash; with an LLM-powered fortune generator orchestrated reliably through Temporal.

**KO** &mdash; 한국에서 가장 인기 있는 두 가지 트렌드인 **사주(四柱)**와 **MBTI**를 결합하고, LLM 기반 AI가 맞춤형 운세를 생성하는 Temporal 워크플로우 데모입니다.

Highlights: activity orchestration, automatic LLM retries, workflow queries, deterministic replay. / 액티비티 오케스트레이션, 자동 LLM 재시도, 워크플로우 쿼리, 결정론적 리플레이.

### [Demo 2: Logistics & Fulfillment Service / 물류 및 주문 처리 서비스](./demo-2-logistics)

> Temporal Python SDK | Saga Pattern | Human-in-the-Loop | Real-time Tracking

**EN** &mdash; A mock logistics and order fulfillment pipeline demonstrating multi-step orchestration, the saga pattern for automatic rollback, human approval via signals, and real-time order tracking via queries.

**KO** &mdash; 다단계 오케스트레이션, 자동 롤백을 위한 사가(Saga) 패턴, 시그널을 통한 승인, 쿼리를 통한 실시간 주문 추적을 시연하는 모의 물류/주문 처리 파이프라인입니다.

Highlights: saga compensation, signals, queries, durable timers, retry with backoff. / 사가 보상, 시그널, 쿼리, 내구성 타이머, 백오프 재시도.

---

## Quick Start / 빠른 시작

### Prerequisites / 사전 준비

- Python 3.11+
- [`just`](https://just.systems/) (`brew install just`)
- The [Temporal CLI](https://docs.temporal.io/cli) (`brew install temporal`)
- A `.env` file at the project root (see [Configuration](#configuration--설정))

### Setup / 설치

```bash
# Install dependencies for both demos / 두 데모의 의존성 설치
just setup-all
```

### Start the Temporal dev server / Temporal 개발 서버 시작

```bash
# Local server + Web UI at http://localhost:8233
just temporal-server
```

### Run a demo / 데모 실행

```bash
# Demo 1 — Korean Fortune / 한국 운세
just fortune-worker            # Terminal 1: worker / 워커
just fortune-start             # Terminal 2: run a reading / 운세 실행

# Demo 2 — Logistics / 물류
just logistics-worker          # Terminal 1: worker / 워커
just logistics-start           # Terminal 2: create an order / 주문 생성
```

Run `just` (or `just --list`) to see all available recipes. / 사용 가능한 모든 레시피는 `just`로 확인하세요.

---

## Configuration / 설정

**EN** &mdash; Both demos read connection settings from environment variables loaded from a `.env` file at the project root, so the same code runs against a local server or Temporal Cloud.

**KO** &mdash; 두 데모 모두 프로젝트 루트의 `.env` 파일에서 연결 설정을 읽으므로, 동일한 코드로 로컬 서버와 Temporal Cloud 모두에 연결할 수 있습니다.

| Variable | Description | Local / 로컬 |
|---|---|---|
| `TEMPORAL_ADDRESS` | Frontend `host:port` | `localhost:7233` |
| `TEMPORAL_NAMESPACE` | Namespace | `default` |
| `TEMPORAL_API_KEY` | Cloud API key (TLS auto-enabled when set) | *(empty)* |
| `OPENAI_API_KEY` | OpenAI key for Demo 1 (falls back to a mock fortune if unset) | *(optional)* |

See each demo's README for the full connection guide (local vs. Temporal Cloud). / 로컬과 Temporal Cloud 연결 방법은 각 데모의 README를 참고하세요.

---

## Repository Structure / 저장소 구조

```
temporal-demo/
  justfile                     # Root task runner (orchestrates both demos)
  demo-1-korean-fortune/       # Agentic AI demo (Saju + MBTI + LLM)
  demo-2-logistics/            # Logistics / fulfillment demo (saga, signals, queries)
```

Each demo is independent, with its own `justfile`, `pyproject.toml`, tests, and detailed README. / 각 데모는 독립적이며 자체 `justfile`, `pyproject.toml`, 테스트, 상세 README를 갖습니다.

---

## Tests / 테스트

```bash
cd demo-1-korean-fortune && just test    # 25 tests
cd demo-2-logistics && just test         # 4 tests
```

---

## License / 라이선스

See [LICENSE](./LICENSE).
