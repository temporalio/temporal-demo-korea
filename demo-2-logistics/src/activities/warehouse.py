"""Warehouse / inventory activities."""

from __future__ import annotations

import asyncio
import random
import uuid

from temporalio import activity

from src.models import Order, OrderItem


@activity.defn
async def check_inventory(items: list[OrderItem]) -> bool:
    """Check whether every item is in stock (simulated)."""
    activity.logger.info("Checking inventory for %d line item(s) ...", len(items))
    await asyncio.sleep(random.uniform(0.3, 0.8))
    # Simulate: 95 % chance everything is in stock
    in_stock = random.random() < 0.95
    if not in_stock:
        activity.logger.warning("One or more items out of stock!")
    else:
        activity.logger.info("All items in stock.")
    return in_stock


@activity.defn
async def reserve_inventory(order: Order) -> str:
    """Reserve items in the warehouse. Returns a reservation ID."""
    activity.logger.info(
        "Reserving inventory for order %s (%d item(s)) ...",
        order.order_id,
        len(order.items),
    )
    await asyncio.sleep(random.uniform(0.5, 1.0))
    reservation_id = f"RSV-{uuid.uuid4().hex[:8].upper()}"
    activity.logger.info("Inventory reserved: %s", reservation_id)
    return reservation_id


@activity.defn
async def release_inventory(reservation_id: str) -> bool:
    """Compensating action: release a previous inventory reservation."""
    activity.logger.info("Releasing inventory reservation %s ...", reservation_id)
    await asyncio.sleep(0.3)
    activity.logger.info("Reservation %s released.", reservation_id)
    return True


@activity.defn
async def return_items_to_shelf(order: Order) -> bool:
    """Compensating action: return picked items back to shelf."""
    activity.logger.info("Returning picked items to shelf for order %s ...", order.order_id)
    await asyncio.sleep(0.5)
    activity.logger.info("Items returned to shelf for order %s.", order.order_id)
    return True


@activity.defn
async def unpack_order(package_label: str) -> bool:
    """Compensating action: unpack a previously packed order."""
    activity.logger.info("Unpacking package %s ...", package_label)
    await asyncio.sleep(0.4)
    activity.logger.info("Package %s unpacked.", package_label)
    return True


@activity.defn
async def pick_items(order: Order) -> bool:
    """Simulate warehouse staff picking items (2-3 s)."""
    activity.logger.info("Picking items for order %s ...", order.order_id)
    await asyncio.sleep(random.uniform(2.0, 3.0))
    activity.logger.info("All items picked for order %s.", order.order_id)
    return True


@activity.defn
async def pack_order(order: Order) -> str:
    """Simulate packing. Returns a package tracking label."""
    activity.logger.info("Packing order %s ...", order.order_id)
    await asyncio.sleep(random.uniform(1.0, 2.0))
    label = f"PKG-{uuid.uuid4().hex[:8].upper()}"
    activity.logger.info("Order %s packed  label=%s", order.order_id, label)
    return label
