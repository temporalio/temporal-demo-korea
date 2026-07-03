"""Payment-related activities."""

from __future__ import annotations

import asyncio
import random
import uuid

from temporalio import activity

from src.models import Order


@activity.defn
async def process_payment(order: Order) -> str:
    """Simulate payment processing. Returns a transaction ID.

    Randomly fails ~10 % of the time to demonstrate Temporal retries.
    """
    activity.logger.info(
        "Processing payment of $%.2f for order %s ...",
        order.total_amount,
        order.order_id,
    )
    # Simulate latency
    await asyncio.sleep(random.uniform(1.0, 2.0))

    # Simulate occasional failures
    if random.random() < 0.10:
        raise RuntimeError(
            f"Payment gateway timeout for order {order.order_id} "
            "(transient error - will be retried)"
        )

    transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    activity.logger.info(
        "Payment confirmed for order %s  txn=%s",
        order.order_id,
        transaction_id,
    )
    return transaction_id


@activity.defn
async def refund_payment(order: Order, transaction_id: str) -> bool:
    """Compensating action: refund a previously-processed payment."""
    activity.logger.info(
        "Refunding payment txn=%s ($%.2f) for order %s ...",
        transaction_id,
        order.total_amount,
        order.order_id,
    )
    await asyncio.sleep(0.5)
    activity.logger.info("Refund complete for txn=%s", transaction_id)
    return True
