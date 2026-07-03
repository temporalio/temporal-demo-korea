# Demo 2 -- Logistics / Fulfillment Service

Temporal sales-event demo for Korea. This project showcases a mock logistics and
fulfillment pipeline built with the **Temporal Python SDK**.

## Quick start

```bash
# 1. Install dependencies
just setup

# 2. Make sure a local Temporal server is running
#    (e.g. `temporal server start-dev`)

# 3. Start the worker
just worker

# 4. In another terminal, start an order workflow
just start                  # normal order (~$240)
just start --high-value     # order >$1,000 requiring human approval
just start --fail           # order that triggers saga compensation
```

## Scenarios

### Normal order (happy path)
```bash
just start
```
Runs through payment, inventory reservation, picking, packing, shipping, and
delivery. Watch the worker terminal for step-by-step progress.

### High-value order (human-in-the-loop)
```bash
just start --high-value
```
The order total exceeds $1,000, so the workflow pauses and waits for a manager
to approve it via a Temporal signal. In a second terminal, run:
```bash
just approve ORD-XXXXXXXX
```
If no approval arrives within 5 minutes, the workflow times out and triggers
saga compensation.

### Tracking a running order
```bash
just track ORD-XXXXXXXX
```
Uses a Temporal query to fetch the live order state without interrupting the
workflow.

### Failure + saga compensation
```bash
just start --fail
```
Demonstrates the saga pattern: after one step fails, Temporal automatically
runs compensating actions in reverse order (cancel shipment, release inventory,
refund payment).

## Architecture

```
src/
  models.py                  -- Pydantic/dataclass domain models
  activities/
    payment.py               -- process_payment, refund_payment
    warehouse.py             -- check/reserve/release inventory, pick, pack
    shipping.py              -- arrange_shipment, cancel_shipment
    notifications.py         -- send_notification (simulated email)
  workflows/
    order_workflow.py        -- OrderFulfillmentWorkflow (the orchestrator)
  worker.py                  -- Temporal worker process
  starter.py                 -- CLI to start a workflow
  approve.py                 -- CLI to send approval signal
  track.py                   -- CLI to query live order status
tests/
  test_workflow.py           -- Unit tests with mocked activities
```

## Key selling points

1. **Saga pattern** -- If any step fails, compensating transactions run in
   reverse order. No manual cleanup, no orphaned state.

2. **Human-in-the-loop** -- High-value orders pause until a human sends an
   approval signal. The workflow sleeps durably; even if the worker restarts,
   the approval is not lost.

3. **Durability** -- Every step is persisted. Kill the worker mid-pipeline,
   restart it, and the order picks up exactly where it left off.

4. **Visibility** -- Query the workflow at any time to see the current status,
   full history, and shipment details. No polling a database.

5. **Retries with back-off** -- Payment processing retries automatically with
   exponential back-off. Transient failures are handled without custom code.

## Tech stack

- Python 3.11+
- Temporal Python SDK (`temporalio`)
- Pydantic v2 / dataclasses for models
- pytest + pytest-asyncio for tests
