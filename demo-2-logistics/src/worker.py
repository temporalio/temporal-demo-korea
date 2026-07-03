"""Temporal worker for the Logistics / Fulfillment demo.

Run with:  python -m src.worker
"""

from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()  # load .env from project root

from temporalio.worker import Worker

from src import get_client
from src.activities.notifications import send_notification
from src.activities.payment import process_payment, refund_payment
from src.activities.shipping import arrange_shipment, cancel_shipment
from src.activities.warehouse import (
    check_inventory,
    pack_order,
    pick_items,
    release_inventory,
    reserve_inventory,
    return_items_to_shelf,
    unpack_order,
)
from src.workflows.order_workflow import OrderFulfillmentWorkflow

TASK_QUEUE = "logistics-queue"


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    banner = r"""
    ╔══════════════════════════════════════════════════════════╗
    ║   Temporal Demo 2 -- Logistics / Fulfillment Service    ║
    ║   Task Queue: logistics-queue                           ║
    ║   Waiting for workflows ...                             ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)

    client = await get_client()

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[OrderFulfillmentWorkflow],
        activities=[
            process_payment,
            refund_payment,
            check_inventory,
            reserve_inventory,
            release_inventory,
            pick_items,
            pack_order,
            arrange_shipment,
            cancel_shipment,
            return_items_to_shelf,
            unpack_order,
            send_notification,
        ],
    )

    print(f"Worker started on task queue '{TASK_QUEUE}'. Press Ctrl+C to stop.\n")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
