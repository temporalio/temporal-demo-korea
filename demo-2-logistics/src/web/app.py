"""FastAPI web application for the Logistics / Fulfillment demo.

Serves:
  - Customer UI (/) : browse products, place orders, track shipments
  - Admin UI (/admin) : view all orders, approve/cancel, monitor pipeline

All order operations go through Temporal workflows.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from temporalio.client import Client
from temporalio.service import RPCError

from src import get_client
from src.models import Address, Order, OrderItem, OrderState, OrderStatus
from src.workflows.order_workflow import OrderFulfillmentWorkflow

TASK_QUEUE = "logistics-queue"
STATIC_DIR = Path(__file__).parent / "static"

# Product catalog
PRODUCTS = [
    {"sku": "GALAXY-BUDS3", "name": "Samsung Galaxy Buds3 Pro", "price": 199_000, "image": "headphones", "category": "Audio"},
    {"sku": "LG-GRAM-17", "name": "LG Gram 17\" Laptop", "price": 1_950_000, "image": "laptop", "category": "Computers"},
    {"sku": "KAKAO-RYAN", "name": "Kakao Friends Ryan Plush", "price": 39_000, "image": "toy", "category": "Lifestyle"},
    {"sku": "GALAXY-S25", "name": "Samsung Galaxy S25 Ultra", "price": 1_690_000, "image": "phone", "category": "Phones"},
    {"sku": "ROCKET-BOX", "name": "Coupang Rocket Delivery Box Set", "price": 65_000, "image": "box", "category": "Lifestyle"},
    {"sku": "ARTISAN-KB", "name": "Korean Artisan Mechanical Keyboard", "price": 390_000, "image": "keyboard", "category": "Accessories"},
    {"sku": "BTS-LIGHTSTICK", "name": "BTS Official Light Stick Ver.4", "price": 78_000, "image": "lightstick", "category": "K-Pop"},
    {"sku": "HANBOK-DRESS", "name": "Modern Hanbok Dress", "price": 249_000, "image": "dress", "category": "Fashion"},
]

# Temporal client (initialized on startup)
_client: Client | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    _client = await get_client()
    yield


app = FastAPI(title="Logistics Fulfillment Demo", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _get_client() -> Client:
    assert _client is not None, "Temporal client not initialized"
    return _client


# ── Page routes ──────────────────────────────────────────────────────────────

@app.get("/")
async def customer_page():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin")
async def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


# ── API: Products ────────────────────────────────────────────────────────────

@app.get("/api/products")
async def list_products():
    return PRODUCTS


# ── API: Orders ──────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    customer_name: str
    customer_email: str
    items: list[dict]  # [{sku, quantity}]
    shipping_address: dict  # {street, city, state, zip_code, country}


@app.post("/api/orders")
async def create_order(req: CreateOrderRequest):
    """Create an order and start the fulfillment workflow."""
    client = _get_client()
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    # Map SKU -> product
    product_map = {p["sku"]: p for p in PRODUCTS}
    order_items = []
    for item in req.items:
        product = product_map.get(item["sku"])
        if not product:
            raise HTTPException(400, f"Unknown SKU: {item['sku']}")
        order_items.append(OrderItem(
            sku=item["sku"],
            name=product["name"],
            quantity=item["quantity"],
            unit_price=product["price"],
        ))

    order = Order(
        order_id=order_id,
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        items=order_items,
        shipping_address=Address(**req.shipping_address),
    )

    handle = await client.start_workflow(
        OrderFulfillmentWorkflow.run,
        order,
        id=order_id,
        task_queue=TASK_QUEUE,
    )

    return {
        "order_id": order_id,
        "total_amount": order.total_amount,
        "requires_approval": order.requires_approval,
        "workflow_id": handle.id,
    }


@app.get("/api/orders")
async def list_orders():
    """List all order workflows (via Temporal visibility)."""
    client = _get_client()
    orders: list[dict[str, Any]] = []

    async for wf in client.list_workflows('WorkflowType = "OrderFulfillmentWorkflow"'):
        order_info: dict[str, Any] = {
            "workflow_id": wf.id,
            "status": wf.status.name if wf.status else "UNKNOWN",
            "start_time": wf.start_time.isoformat() if wf.start_time else None,
            "close_time": wf.close_time.isoformat() if wf.close_time else None,
        }
        orders.append(order_info)

    return orders


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    """Get current order state by querying the running workflow."""
    client = _get_client()
    handle = client.get_workflow_handle(order_id)

    try:
        state: OrderState = await handle.query(OrderFulfillmentWorkflow.get_status)
    except RPCError as e:
        raise HTTPException(404, f"Order not found or workflow completed: {e}")

    return _serialize_order_state(state)


@app.post("/api/orders/{order_id}/approve")
async def approve_order(order_id: str):
    """Send approval signal to a pending order."""
    client = _get_client()
    handle = client.get_workflow_handle(order_id)

    try:
        await handle.signal(OrderFulfillmentWorkflow.approve)
    except RPCError as e:
        raise HTTPException(400, f"Cannot approve: {e}")

    return {"message": f"Approval signal sent to {order_id}"}


@app.post("/api/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    """Send cancel signal to a running order."""
    client = _get_client()
    handle = client.get_workflow_handle(order_id)

    try:
        await handle.signal(OrderFulfillmentWorkflow.cancel)
    except RPCError as e:
        raise HTTPException(400, f"Cannot cancel: {e}")

    return {"message": f"Cancel signal sent to {order_id}"}


@app.post("/api/orders/{order_id}/advance-pick")
async def advance_pick(order_id: str):
    """Signal the workflow to start warehouse picking."""
    client = _get_client()
    handle = client.get_workflow_handle(order_id)

    try:
        await handle.signal(OrderFulfillmentWorkflow.advance_to_pick)
    except RPCError as e:
        raise HTTPException(400, f"Cannot advance: {e}")

    return {"message": f"Pick signal sent to {order_id}"}


@app.post("/api/orders/{order_id}/advance-pack")
async def advance_pack(order_id: str):
    """Signal the workflow to start packing."""
    client = _get_client()
    handle = client.get_workflow_handle(order_id)

    try:
        await handle.signal(OrderFulfillmentWorkflow.advance_to_pack)
    except RPCError as e:
        raise HTTPException(400, f"Cannot advance: {e}")

    return {"message": f"Pack signal sent to {order_id}"}


@app.post("/api/orders/{order_id}/advance-ship")
async def advance_ship(order_id: str):
    """Signal the workflow to ship the order."""
    client = _get_client()
    handle = client.get_workflow_handle(order_id)

    try:
        await handle.signal(OrderFulfillmentWorkflow.advance_to_ship)
    except RPCError as e:
        raise HTTPException(400, f"Cannot advance: {e}")

    return {"message": f"Ship signal sent to {order_id}"}


@app.post("/api/orders/{order_id}/confirm-delivery")
async def confirm_delivery(order_id: str):
    """Signal the workflow that delivery is confirmed."""
    client = _get_client()
    handle = client.get_workflow_handle(order_id)

    try:
        await handle.signal(OrderFulfillmentWorkflow.confirm_delivery)
    except RPCError as e:
        raise HTTPException(400, f"Cannot confirm delivery: {e}")

    return {"message": f"Delivery confirmation sent to {order_id}"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialize_order_state(state: OrderState) -> dict:
    """Convert OrderState dataclass to JSON-safe dict."""
    order = state.order
    return {
        "order_id": order.order_id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "items": [
            {"sku": i.sku, "name": i.name, "quantity": i.quantity, "unit_price": i.unit_price}
            for i in order.items
        ],
        "shipping_address": {
            "street": order.shipping_address.street,
            "city": order.shipping_address.city,
            "state": order.shipping_address.state,
            "zip_code": order.shipping_address.zip_code,
            "country": order.shipping_address.country,
        },
        "total_amount": order.total_amount,
        "requires_approval": order.requires_approval,
        "status": state.status,
        "shipment": {
            "tracking_number": state.shipment.tracking_number,
            "carrier": state.shipment.carrier,
            "estimated_delivery": state.shipment.estimated_delivery,
        } if state.shipment else None,
        "status_history": [
            {"status": s, "timestamp": t} for s, t in state.status_history
        ],
        "failure_reason": state.failure_reason,
        "compensations_run": state.compensations_run,
    }
