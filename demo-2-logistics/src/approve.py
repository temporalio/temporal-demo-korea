"""CLI to send an approval signal to a running OrderFulfillmentWorkflow.

Usage:
    python -m src.approve ORD-XXXXXXXX

Run with:  just approve ORD-XXXXXXXX
"""

from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv

load_dotenv()

from src import get_client
from src.workflows.order_workflow import OrderFulfillmentWorkflow


async def main() -> None:
    parser = argparse.ArgumentParser(description="Approve a pending order")
    parser.add_argument("order_id", help="The order / workflow ID to approve")
    args = parser.parse_args()

    client = await get_client()
    handle = client.get_workflow_handle(args.order_id)

    print(f"Sending APPROVE signal to workflow {args.order_id} ...")
    await handle.signal(OrderFulfillmentWorkflow.approve)
    print("Signal sent successfully!")


if __name__ == "__main__":
    asyncio.run(main())
