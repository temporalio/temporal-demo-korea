# Demo 2: Logistics & Fulfillment Service / 물류 및 주문 처리 서비스

> Temporal Python SDK | Saga Pattern | Human-in-the-Loop | Real-time Tracking

---

## Overview / 개요

**EN** &mdash; A mock logistics and order fulfillment pipeline that demonstrates Temporal's core strengths: multi-step orchestration, the saga pattern for automatic rollback, human-in-the-loop approval via signals, and real-time order tracking via queries.

**KO** &mdash; Temporal의 핵심 기능을 보여주는 모의 물류/주문 처리 파이프라인입니다. 다단계 오케스트레이션, 자동 롤백을 위한 사가(Saga) 패턴, 시그널을 통한 사람의 개입(Human-in-the-Loop) 승인, 쿼리를 통한 실시간 주문 추적을 시연합니다.

### What does it demonstrate? / 무엇을 보여주나요?

| Temporal Feature | EN | KO |
|---|---|---|
| Saga pattern | Automatic compensating transactions on failure | 실패 시 자동 보상 트랜잭션 |
| Signals | Human approval for high-value orders | 고가 주문에 대한 사람의 승인 |
| Queries | Real-time order status without polling a DB | DB 폴링 없이 실시간 주문 상태 조회 |
| Durable sleep | Workflow survives worker restarts mid-delivery | 배송 중 워커 재시작에도 워크플로우 유지 |
| Retry with backoff | Payment processing retries automatically | 결제 처리 자동 재시도 |

---

## Quick Start / 빠른 시작

### Prerequisites / 사전 준비

- Python 3.11+
- [just](https://just.systems/) (`brew install just`)
- `.env` file at the project root with `TEMPORAL_API_KEY`

### Setup / 설치

```bash
just setup
```

### Run / 실행

```bash
# Terminal 1: Start the worker / 워커 시작
just worker
```

---

## Scenarios / 시나리오

### 1. Normal Order (Happy Path) / 일반 주문

```bash
just start
```

**EN** &mdash; Creates a ~$240 order and runs through the full pipeline: payment &#8594; inventory reservation &#8594; picking &#8594; packing &#8594; shipping &#8594; delivery. Watch the worker terminal for step-by-step progress.

**KO** &mdash; 약 $240 주문을 생성하고 전체 파이프라인을 실행합니다: 결제 &#8594; 재고 예약 &#8594; 피킹 &#8594; 포장 &#8594; 배송 &#8594; 배달. 워커 터미널에서 단계별 진행 상황을 확인하세요.

### 2. High-Value Order (Human-in-the-Loop) / 고가 주문 (승인 필요)

```bash
# Terminal 2: Start a high-value order / 고가 주문 시작
just start --high-value

# Terminal 3: Approve it / 승인
just approve ORD-XXXXXXXX
```

**EN** &mdash; Orders over $1,000 require manager approval. The workflow pauses durably and waits up to 5 minutes for an `approve` signal. If no approval arrives, saga compensation kicks in automatically.

**KO** &mdash; $1,000 이상의 주문은 관리자 승인이 필요합니다. 워크플로우가 내구성 있게 일시 중지되고 최대 5분간 `approve` 시그널을 기다립니다. 승인이 없으면 사가 보상이 자동으로 시작됩니다.

### 3. Order Tracking (Queries) / 주문 추적 (쿼리)

```bash
just track ORD-XXXXXXXX
```

**EN** &mdash; Queries the live workflow state: current status, full history timeline, shipment tracking info. No database, no polling &mdash; just Temporal queries.

**KO** &mdash; 실행 중인 워크플로우의 상태를 조회합니다: 현재 상태, 전체 이력 타임라인, 배송 추적 정보. 데이터베이스도 폴링도 필요 없이 Temporal 쿼리만으로 가능합니다.

### 4. Failure + Saga Compensation / 실패 + 사가 보상

```bash
just start --fail
```

**EN** &mdash; Triggers a failure mid-pipeline. Temporal automatically runs compensating actions in reverse order:

1. Cancel shipment / 배송 취소
2. Release inventory / 재고 해제
3. Refund payment / 결제 환불

No manual cleanup. No orphaned state. No custom error-handling spaghetti.

**KO** &mdash; 파이프라인 중간에 실패를 발생시킵니다. Temporal이 자동으로 역순으로 보상 작업을 실행합니다. 수동 정리 작업도, 고아 상태도, 복잡한 에러 처리 코드도 필요 없습니다.

---

## Architecture / 아키텍처

```
Order
  |
  v
OrderFulfillmentWorkflow (Temporal Workflow)
  |
  |-- Step 1: process_payment        (Activity, retry x3)
  |-- Step 2: [await approve signal] (Signal, if order > $1,000)
  |-- Step 3: reserve_inventory      (Activity)
  |-- Step 4: pick_items             (Activity)
  |-- Step 5: pack_order             (Activity)
  |-- Step 6: arrange_shipment       (Activity)
  |-- Step 7: send_notification      (Activity - "shipped!")
  |-- Step 8: workflow.sleep(5)      (Durable timer - simulates transit)
  |-- Step 9: send_notification      (Activity - "delivered!")
  |
  v
OrderState (status, shipment_info, full_history)

--- On failure at any step / 어느 단계에서든 실패 시 ---

SAGA COMPENSATION (reverse order / 역순 보상):
  cancel_shipment -> release_inventory -> refund_payment
```

---

## File Structure / 파일 구조

```
demo-2-logistics/
  pyproject.toml                  # Dependencies: temporalio, pydantic
  justfile                        # setup, worker, start, approve, track, test
  src/
    __init__.py                   # Temporal Cloud connection helper
    models.py                     # Order, OrderItem, Address, OrderState, OrderStatus
    worker.py                     # Worker on task queue: logistics-queue
    starter.py                    # CLI: --high-value, --fail
    approve.py                    # CLI: send approval signal / 승인 시그널 전송
    track.py                      # CLI: query live order status / 실시간 주문 상태 조회
    activities/
      payment.py                  # process_payment (10% fail rate), refund_payment
      warehouse.py                # reserve/release inventory, pick, pack
      shipping.py                 # arrange/cancel shipment (Korean carriers)
      notifications.py            # Console-based notification simulation
    workflows/
      order_workflow.py           # 8-step pipeline + saga compensation
  tests/
    test_workflow.py              # 4 unit tests (happy path, approval, saga, query)
```

---

## Why Temporal? / 왜 Temporal인가?

**EN**

1. **Saga pattern without the boilerplate** &mdash; Define your compensations as regular activities. Temporal guarantees they run even if the worker crashes during rollback.
2. **Human-in-the-loop, built in** &mdash; Signals let workflows wait for human input (approvals, reviews, escalations) durably. No external queue or state machine needed.
3. **Durability by default** &mdash; Every step is persisted. Kill the worker mid-pipeline, restart it, and the order picks up exactly where it left off. Durable `workflow.sleep()` survives restarts.
4. **Real-time visibility** &mdash; Query any running workflow for its current state. View the full execution history in the Temporal UI. No custom dashboards or observability stacks required.
5. **Retries with exponential backoff** &mdash; Payment processing retries automatically with configurable backoff. Transient failures are absorbed without custom try/except code.

**KO**

1. **보일러플레이트 없는 사가 패턴** &mdash; 보상 작업을 일반 액티비티로 정의하세요. 롤백 중 워커가 충돌하더라도 Temporal이 실행을 보장합니다.
2. **기본 제공되는 Human-in-the-Loop** &mdash; 시그널을 통해 워크플로우가 사람의 입력(승인, 검토, 에스컬레이션)을 내구성 있게 기다릴 수 있습니다. 외부 큐나 상태 머신이 필요 없습니다.
3. **기본 내구성** &mdash; 모든 단계가 저장됩니다. 파이프라인 중간에 워커를 종료하고 다시 시작해도 주문이 정확히 중단된 지점에서 재개됩니다. `workflow.sleep()`도 재시작에서 살아남습니다.
4. **실시간 가시성** &mdash; 실행 중인 워크플로우의 현재 상태를 언제든 조회할 수 있습니다. Temporal UI에서 전체 실행 이력을 확인하세요. 별도의 대시보드나 관측 스택이 필요 없습니다.
5. **지수 백오프 재시도** &mdash; 결제 처리가 구성 가능한 백오프로 자동 재시도됩니다. 일시적 실패가 별도의 try/except 코드 없이 흡수됩니다.
