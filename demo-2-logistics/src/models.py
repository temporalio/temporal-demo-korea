"""Domain models for the Logistics / Fulfillment demo."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OrderStatus(str, Enum):
    """Every state an order can pass through."""

    RECEIVED = "RECEIVED"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AWAITING_PICK = "AWAITING_PICK"
    PICKING = "PICKING"
    PICKED = "PICKED"
    AWAITING_PACK = "AWAITING_PACK"
    PACKING = "PACKING"
    PACKED = "PACKED"
    AWAITING_SHIP = "AWAITING_SHIP"
    SHIPPING = "SHIPPING"
    IN_TRANSIT = "IN_TRANSIT"
    AWAITING_DELIVERY = "AWAITING_DELIVERY"
    DELIVERED = "DELIVERED"
    COMPENSATING = "COMPENSATING"
    CANCELLED = "CANCELLED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURNED = "RETURNED"


@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "KR"


@dataclass
class OrderItem:
    sku: str
    name: str
    quantity: int
    unit_price: float


@dataclass
class Order:
    order_id: str
    customer_name: str
    customer_email: str
    items: list[OrderItem]
    shipping_address: Address

    @property
    def total_amount(self) -> float:
        return sum(item.unit_price * item.quantity for item in self.items)

    @property
    def requires_approval(self) -> bool:
        return self.total_amount >= 1_000_000


@dataclass
class ShipmentInfo:
    tracking_number: str
    carrier: str
    estimated_delivery: str


@dataclass
class OrderState:
    order: Order
    status: str = OrderStatus.RECEIVED.value
    shipment: Optional[ShipmentInfo] = None
    status_history: list[tuple[str, str]] = field(default_factory=list)
    failure_reason: Optional[str] = None
    compensations_run: list[str] = field(default_factory=list)
