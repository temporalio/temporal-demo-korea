"""CLI to query the current status of a running OrderFulfillmentWorkflow.

Usage:
    python -m src.track ORD-XXXXXXXX

Run with:  just track ORD-XXXXXXXX
"""

from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv

load_dotenv()

from src import get_client
from src.models import OrderState
from src.workflows.order_workflow import OrderFulfillmentWorkflow


def _print_state(state: OrderState) -> None:
    """Pretty-print an OrderState."""
    o = state.order
    print(f"\n{'=' * 60}")
    print(f"  Order Tracking: {o.order_id}")
    print(f"{'=' * 60}")
    print(f"  Customer:      {o.customer_name} <{o.customer_email}>")
    print(f"  Total:         \u20a9{o.total_amount:,.0f}")
    print(f"  Current Status: {state.status}")
    if state.shipment:
        print(f"  Tracking #:    {state.shipment.tracking_number}")
        print(f"  Carrier:       {state.shipment.carrier}")
        print(f"  ETA:           {state.shipment.estimated_delivery}")
    if state.failure_reason:
        print(f"  Failure:       {state.failure_reason}")
    print(f"\n  Items:")
    for item in o.items:
        print(f"    - {item.name} (x{item.quantity})  ${item.unit_price * item.quantity:,.2f}")
    print(f"\n  Shipping Address:")
    addr = o.shipping_address
    print(f"    {addr.street}")
    print(f"    {addr.city}, {addr.state} {addr.zip_code}")
    print(f"    {addr.country}")
    print(f"\n  Status History:")
    for status, ts in state.status_history:
        print(f"    {ts}  {status}")
    print(f"{'=' * 60}\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Track an order's current status")
    parser.add_argument("order_id", help="The order / workflow ID to query")
    args = parser.parse_args()

    client = await get_client()
    handle = client.get_workflow_handle(args.order_id)

    print(f"Querying workflow {args.order_id} ...")
    state: OrderState = await handle.query(OrderFulfillmentWorkflow.get_status)
    _print_state(state)


if __name__ == "__main__":
    asyncio.run(main())
