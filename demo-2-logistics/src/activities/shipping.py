"""Shipping / carrier activities."""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta

from temporalio import activity

from src.models import Order, ShipmentInfo


_CARRIERS = ["CJ Logistics", "Hanjin Express", "Lotte Global Logistics", "Korea Post"]


@activity.defn
async def arrange_shipment(order: Order, package_label: str) -> ShipmentInfo:
    """Create a shipment with a carrier and return tracking info."""
    carrier = random.choice(_CARRIERS)
    activity.logger.info(
        "Arranging shipment for order %s via %s  label=%s ...",
        order.order_id,
        carrier,
        package_label,
    )
    await asyncio.sleep(random.uniform(1.0, 2.0))

    tracking_number = f"KR{uuid.uuid4().hex[:10].upper()}"
    estimated = (datetime.now() + timedelta(days=random.randint(1, 3))).strftime(
        "%Y-%m-%d"
    )
    shipment = ShipmentInfo(
        tracking_number=tracking_number,
        carrier=carrier,
        estimated_delivery=estimated,
    )
    activity.logger.info(
        "Shipment created  tracking=%s  carrier=%s  ETA=%s",
        shipment.tracking_number,
        shipment.carrier,
        shipment.estimated_delivery,
    )
    return shipment


@activity.defn
async def cancel_shipment(tracking_number: str) -> bool:
    """Compensating action: cancel a previously-created shipment."""
    activity.logger.info("Cancelling shipment %s ...", tracking_number)
    await asyncio.sleep(0.3)
    activity.logger.info("Shipment %s cancelled.", tracking_number)
    return True
