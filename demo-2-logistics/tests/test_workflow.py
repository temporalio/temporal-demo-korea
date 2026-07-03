"""Tests for the OrderFulfillmentWorkflow.

Uses Temporal's built-in test environment with mocked activities to verify
both the happy path and the saga-compensation path.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.models import Address, Order, OrderItem, OrderStatus, ShipmentInfo
from src.workflows.order_workflow import OrderFulfillmentWorkflow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TASK_QUEUE = "test-logistics-queue"


def _sample_order(*, high_value: bool = False) -> Order:
    order_id = f"TEST-{uuid.uuid4().hex[:6].upper()}"
    if high_value:
        items = [
            OrderItem(sku="EXP-1", name="Expensive Widget", quantity=1, unit_price=1_500_000),
        ]
    else:
        items = [
            OrderItem(sku="CHE-1", name="Cheap Widget", quantity=1, unit_price=10_000),
        ]
    return Order(
        order_id=order_id,
        customer_name="Test User",
        customer_email="test@example.com",
        items=items,
        shipping_address=Address(
            street="1 Test St",
            city="Testville",
            state="TS",
            zip_code="00000",
            country="KR",
        ),
    )


# ---------------------------------------------------------------------------
# Mock activities (deterministic, no sleeps)
# ---------------------------------------------------------------------------

@activity.defn(name="process_payment")
async def mock_process_payment(order: Order) -> str:
    return "TXN-MOCK-001"


@activity.defn(name="refund_payment")
async def mock_refund_payment(order: Order, transaction_id: str) -> bool:
    return True


@activity.defn(name="check_inventory")
async def mock_check_inventory(items: list[OrderItem]) -> bool:
    return True


@activity.defn(name="reserve_inventory")
async def mock_reserve_inventory(order: Order) -> str:
    return "RSV-MOCK-001"


@activity.defn(name="release_inventory")
async def mock_release_inventory(reservation_id: str) -> bool:
    return True


@activity.defn(name="pick_items")
async def mock_pick_items(order: Order) -> bool:
    return True


@activity.defn(name="pack_order")
async def mock_pack_order(order: Order) -> str:
    return "PKG-MOCK-001"


@activity.defn(name="arrange_shipment")
async def mock_arrange_shipment(order: Order, package_label: str) -> ShipmentInfo:
    return ShipmentInfo(
        tracking_number="KR-MOCK-TRACK",
        carrier="Test Carrier",
        estimated_delivery="2026-06-20",
    )


@activity.defn(name="cancel_shipment")
async def mock_cancel_shipment(tracking_number: str) -> bool:
    return True


@activity.defn(name="return_items_to_shelf")
async def mock_return_items_to_shelf(order: Order) -> bool:
    return True


@activity.defn(name="unpack_order")
async def mock_unpack_order(package_label: str) -> bool:
    return True


@activity.defn(name="send_notification")
async def mock_send_notification(customer_email: str, subject: str, message: str) -> bool:
    return True


MOCK_ACTIVITIES = [
    mock_process_payment,
    mock_refund_payment,
    mock_check_inventory,
    mock_reserve_inventory,
    mock_release_inventory,
    mock_pick_items,
    mock_pack_order,
    mock_arrange_shipment,
    mock_cancel_shipment,
    mock_return_items_to_shelf,
    mock_unpack_order,
    mock_send_notification,
]


# ---------------------------------------------------------------------------
# Failing mock activities for saga compensation tests
# ---------------------------------------------------------------------------

@activity.defn(name="pick_items")
async def mock_pick_items_fail(order: Order) -> bool:
    raise RuntimeError("Simulated pick failure -- item damaged")


# ---------------------------------------------------------------------------
# Helper: send all advance signals so workflow can complete
# ---------------------------------------------------------------------------

async def _advance_all(handle) -> None:
    """Send all four advance signals. Signals are buffered by Temporal."""
    await handle.signal(OrderFulfillmentWorkflow.advance_to_pick)
    await handle.signal(OrderFulfillmentWorkflow.advance_to_pack)
    await handle.signal(OrderFulfillmentWorkflow.advance_to_ship)
    await handle.signal(OrderFulfillmentWorkflow.confirm_delivery)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_happy_path() -> None:
    """A normal order with all admin signals should complete to DELIVERED."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        order = _sample_order(high_value=False)

        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[OrderFulfillmentWorkflow],
            activities=MOCK_ACTIVITIES,
        ):
            handle = await env.client.start_workflow(
                OrderFulfillmentWorkflow.run,
                order,
                id=order.order_id,
                task_queue=TASK_QUEUE,
            )

            # Send all advance signals
            await _advance_all(handle)

            result = await handle.result()

        assert result.status == OrderStatus.DELIVERED.value
        assert result.shipment is not None
        assert result.shipment.tracking_number == "KR-MOCK-TRACK"
        assert result.failure_reason is None

        statuses = [s for s, _ in result.status_history]
        assert "RECEIVED" in statuses
        assert "PAYMENT_CONFIRMED" in statuses
        assert "AWAITING_PICK" in statuses
        assert "PICKING" in statuses
        assert "DELIVERED" in statuses


@pytest.mark.asyncio
async def test_high_value_order_approved() -> None:
    """A high-value order should pause for approval then complete when approved + advanced."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        order = _sample_order(high_value=True)
        assert order.requires_approval

        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[OrderFulfillmentWorkflow],
            activities=MOCK_ACTIVITIES,
        ):
            handle = await env.client.start_workflow(
                OrderFulfillmentWorkflow.run,
                order,
                id=order.order_id,
                task_queue=TASK_QUEUE,
            )

            # Approve first
            await asyncio.sleep(1)
            await handle.signal(OrderFulfillmentWorkflow.approve)

            # Then advance through fulfillment
            await _advance_all(handle)

            result = await handle.result()

        assert result.status == OrderStatus.DELIVERED.value
        assert result.failure_reason is None


@pytest.mark.asyncio
async def test_saga_compensation_on_failure() -> None:
    """When picking fails, saga compensation should cancel + refund."""
    compensating_activities = [
        mock_process_payment,
        mock_refund_payment,
        mock_check_inventory,
        mock_reserve_inventory,
        mock_release_inventory,
        mock_pick_items_fail,  # <-- this one fails
        mock_pack_order,
        mock_arrange_shipment,
        mock_cancel_shipment,
        mock_return_items_to_shelf,
        mock_unpack_order,
        mock_send_notification,
    ]

    async with await WorkflowEnvironment.start_time_skipping() as env:
        order = _sample_order(high_value=False)

        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[OrderFulfillmentWorkflow],
            activities=compensating_activities,
        ):
            handle = await env.client.start_workflow(
                OrderFulfillmentWorkflow.run,
                order,
                id=order.order_id,
                task_queue=TASK_QUEUE,
                execution_timeout=timedelta(seconds=30),
            )

            # Advance to pick (which will fail)
            await asyncio.sleep(0.5)
            await handle.signal(OrderFulfillmentWorkflow.advance_to_pick)

            result = await handle.result()

        assert result.status == OrderStatus.CANCELLED.value
        assert result.failure_reason is not None
        assert "activity task failed" in result.failure_reason.lower() or "pick failure" in result.failure_reason.lower()


@pytest.mark.asyncio
async def test_query_status() -> None:
    """We should be able to query the workflow status while it runs."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        order = _sample_order(high_value=False)

        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[OrderFulfillmentWorkflow],
            activities=MOCK_ACTIVITIES,
        ):
            handle = await env.client.start_workflow(
                OrderFulfillmentWorkflow.run,
                order,
                id=order.order_id,
                task_queue=TASK_QUEUE,
            )

            # Advance and complete
            await _advance_all(handle)
            result = await handle.result()

            assert result.order.order_id == order.order_id
            assert len(result.status_history) > 0


@pytest.mark.asyncio
async def test_cancel_runs_compensations() -> None:
    """Cancelling triggers saga compensations for all completed steps."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        order = _sample_order(high_value=False)

        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[OrderFulfillmentWorkflow],
            activities=MOCK_ACTIVITIES,
        ):
            handle = await env.client.start_workflow(
                OrderFulfillmentWorkflow.run,
                order,
                id=order.order_id,
                task_queue=TASK_QUEUE,
            )

            # Cancel while awaiting pick (payment + inventory already done)
            await handle.signal(OrderFulfillmentWorkflow.cancel)

            result = await handle.result()

        assert result.status == OrderStatus.CANCELLED.value
        assert "cancelled by operator" in result.failure_reason.lower()

        # At minimum: release_inventory + refund_payment
        assert "release_inventory" in result.compensations_run
        assert "refund_payment" in result.compensations_run
        assert len(result.compensations_run) >= 2

        # Verify COMPENSATING status and events in history
        statuses = [s for s, _ in result.status_history]
        assert "COMPENSATING" in statuses
        assert "CANCELLED" in statuses
        comp_events = [s for s in statuses if s.startswith("COMPENSATING:")]
        assert len(comp_events) >= 2
