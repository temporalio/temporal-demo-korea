"""CLI to start an OrderFulfillmentWorkflow.

Usage:
    python -m src.starter                   # normal order (~$500)
    python -m src.starter --high-value      # order >$1000 (requires approval)
    python -m src.starter --fail            # order that will trigger failure + saga

Run with:  just start [--high-value] [--fail]
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from dotenv import load_dotenv

load_dotenv()

from src import get_client
from src.models import Address, Order, OrderItem
from src.worker import TASK_QUEUE
from src.workflows.order_workflow import OrderFulfillmentWorkflow


def _build_order(*, high_value: bool = False, fail: bool = False) -> Order:
    """Build a sample order for demonstration."""
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    if high_value:
        items = [
            OrderItem(sku="LG-GRAM-17", name="LG Gram 17\" Laptop", quantity=1, unit_price=1_950_000),
            OrderItem(sku="ARTISAN-KB", name="Korean Artisan Mechanical Keyboard", quantity=1, unit_price=390_000),
        ]
    elif fail:
        items = [
            OrderItem(sku="WIDGET-FAIL", name="Faulty Widget (test)", quantity=1, unit_price=65_000),
            OrderItem(sku="GADGET-OK", name="Normal Gadget", quantity=1, unit_price=39_000),
        ]
    else:
        items = [
            OrderItem(sku="GALAXY-BUDS3", name="Samsung Galaxy Buds3 Pro", quantity=1, unit_price=199_000),
            OrderItem(sku="KAKAO-RYAN", name="Kakao Friends Ryan Plush", quantity=2, unit_price=39_000),
            OrderItem(sku="BTS-LIGHTSTICK", name="BTS Official Light Stick Ver.4", quantity=1, unit_price=78_000),
        ]

    return Order(
        order_id=order_id,
        customer_name="Kim Minjun",
        customer_email="minjun.kim@example.com",
        items=items,
        shipping_address=Address(
            street="123 Gangnam-daero",
            city="Seoul",
            state="Seoul",
            zip_code="06100",
            country="KR",
        ),
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Start an order fulfillment workflow")
    parser.add_argument("--high-value", action="store_true", help="Create a high-value order (>$1000, requires approval)")
    parser.add_argument("--fail", action="store_true", help="Create an order that will fail (demonstrates saga compensation)")
    args = parser.parse_args()

    order = _build_order(high_value=args.high_value, fail=args.fail)

    print(f"\n{'=' * 60}")
    print(f"  Starting Order Fulfillment Workflow")
    print(f"{'=' * 60}")
    print(f"  Order ID:      {order.order_id}")
    print(f"  Customer:      {order.customer_name}")
    print(f"  Items:         {len(order.items)}")
    print(f"  Total:         \u20a9{order.total_amount:,.0f}")
    print(f"  Approval req:  {order.requires_approval}")
    print(f"{'=' * 60}\n")

    client = await get_client()

    handle = await client.start_workflow(
        OrderFulfillmentWorkflow.run,
        order,
        id=order.order_id,
        task_queue=TASK_QUEUE,
    )

    print(f"Workflow started!  workflow_id={handle.id}  run_id={handle.result_run_id}")

    if order.requires_approval:
        print(
            f"\n  ** This order requires approval! **\n"
            f"  Run:  just approve {order.order_id}\n"
            f"  Or:   python -m src.approve {order.order_id}\n"
        )
        print("Waiting for workflow to complete (approve it in another terminal) ...")
    else:
        print("Waiting for workflow to complete ...")

    result = await handle.result()

    print(f"\n{'=' * 60}")
    print(f"  Workflow Complete!")
    print(f"{'=' * 60}")
    print(f"  Final Status:  {result.status}")
    if result.shipment:
        print(f"  Tracking:      {result.shipment.tracking_number}")
        print(f"  Carrier:       {result.shipment.carrier}")
        print(f"  ETA:           {result.shipment.estimated_delivery}")
    if result.failure_reason:
        print(f"  Failure:       {result.failure_reason}")
    print(f"\n  Status History:")
    for status, ts in result.status_history:
        print(f"    {ts}  {status}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
