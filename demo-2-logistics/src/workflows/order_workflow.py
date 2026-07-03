"""Order Fulfillment Workflow -- the core of the demo.

Demonstrates:
- Multi-step orchestration (payment -> inventory -> pick -> pack -> ship -> deliver)
- Saga pattern with fine-grained compensating transactions on cancel/failure
- Human-in-the-loop: admin must advance each fulfillment step via signal
- Real-time order tracking via Temporal queries
- Durable execution with simulated delays
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from src.activities.notifications import send_notification
    from src.activities.payment import process_payment, refund_payment
    from src.activities.shipping import arrange_shipment, cancel_shipment
    from src.activities.warehouse import (
        pack_order,
        pick_items,
        release_inventory,
        reserve_inventory,
        return_items_to_shelf,
        unpack_order,
    )
    from src.models import Order, OrderState, OrderStatus, ShipmentInfo


# Shared retry policy for compensation activities -- they should try hard
_COMPENSATION_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=5,
)


@workflow.defn
class OrderFulfillmentWorkflow:
    """Orchestrates the full order-fulfillment pipeline with saga compensation.

    Each fulfillment step waits for an admin signal before proceeding.
    Cancellation at ANY point triggers fine-grained saga compensation that
    undoes exactly the steps completed so far, in reverse order.

    Signals:
        approve           -- approve a high-value order awaiting review
        cancel            -- cancel the order at any point before delivery
        advance_to_pick   -- admin confirms: start picking
        advance_to_pack   -- admin confirms: start packing
        advance_to_ship   -- admin confirms: ship the order
        confirm_delivery  -- admin confirms: order delivered

    Queries:
        get_status -- return the current ``OrderState`` snapshot
    """

    def __init__(self) -> None:
        self._state: OrderState  # initialised in run()
        self._approved: bool = False
        self._cancelled: bool = False

        # Admin advancement signals
        self._pick_requested: bool = False
        self._pack_requested: bool = False
        self._ship_requested: bool = False
        self._delivery_confirmed: bool = False

        # Track completed steps so the saga can compensate in reverse
        self._transaction_id: Optional[str] = None
        self._reservation_id: Optional[str] = None
        self._items_picked: bool = False
        self._package_label: Optional[str] = None
        self._tracking_number: Optional[str] = None

    # ------------------------------------------------------------------
    # Main workflow
    # ------------------------------------------------------------------

    @workflow.run
    async def run(self, order: Order) -> OrderState:
        self._state = OrderState(
            order=order,
            status=OrderStatus.RECEIVED.value,
            status_history=[(OrderStatus.RECEIVED.value, workflow.now().isoformat())],
        )

        try:
            # ---- Step 1: Process Payment (automatic with retry) ----
            self._update_status(OrderStatus.PAYMENT_PROCESSING)
            self._transaction_id = await workflow.execute_activity(
                process_payment,
                order,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(seconds=10),
                    maximum_attempts=3,
                ),
            )
            self._update_status(OrderStatus.PAYMENT_CONFIRMED)

            # ---- Step 2: Human approval for high-value orders ----
            if order.requires_approval:
                self._update_status(OrderStatus.AWAITING_APPROVAL)
                await workflow.execute_activity(
                    send_notification,
                    args=[
                        order.customer_email,
                        f"Order {order.order_id} requires approval",
                        (
                            f"Order total \u20a9{order.total_amount:,.0f} exceeds \u20a91,000,000. "
                            "Waiting for manager approval (up to 5 minutes)."
                        ),
                    ],
                    start_to_close_timeout=timedelta(seconds=10),
                )

                try:
                    await workflow.wait_condition(
                        lambda: self._approved or self._cancelled,
                        timeout=timedelta(minutes=5),
                    )
                except TimeoutError:
                    raise ApplicationError("Approval timed out after 5 minutes")

                if self._cancelled:
                    raise ApplicationError("Order cancelled by operator (at approval)")

                workflow.logger.info("Order %s approved!", order.order_id)

            # ---- Step 3: Reserve Inventory (automatic) ----
            self._reservation_id = await workflow.execute_activity(
                reserve_inventory,
                order,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            # ---- Step 4: Wait for admin to start picking ----
            self._update_status(OrderStatus.AWAITING_PICK)
            await self._wait_for_advance(
                lambda: self._pick_requested or self._cancelled,
                "pick",
            )
            if self._cancelled:
                raise ApplicationError("Order cancelled by operator (before pick)")

            self._update_status(OrderStatus.PICKING)
            await workflow.execute_activity(
                pick_items,
                order,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            self._items_picked = True
            self._update_status(OrderStatus.PICKED)

            # ---- Step 5: Wait for admin to start packing ----
            self._update_status(OrderStatus.AWAITING_PACK)
            await self._wait_for_advance(
                lambda: self._pack_requested or self._cancelled,
                "pack",
            )
            if self._cancelled:
                raise ApplicationError("Order cancelled by operator (before pack)")

            self._update_status(OrderStatus.PACKING)
            self._package_label = await workflow.execute_activity(
                pack_order,
                order,
                start_to_close_timeout=timedelta(seconds=30),
            )
            self._update_status(OrderStatus.PACKED)

            # ---- Step 6: Wait for admin to ship ----
            self._update_status(OrderStatus.AWAITING_SHIP)
            await self._wait_for_advance(
                lambda: self._ship_requested or self._cancelled,
                "ship",
            )
            if self._cancelled:
                raise ApplicationError("Order cancelled by operator (before ship)")

            self._update_status(OrderStatus.SHIPPING)
            shipment: ShipmentInfo = await workflow.execute_activity(
                arrange_shipment,
                args=[order, self._package_label],
                start_to_close_timeout=timedelta(seconds=30),
            )
            self._tracking_number = shipment.tracking_number
            self._state.shipment = shipment
            self._update_status(OrderStatus.IN_TRANSIT)

            # ---- Step 7: Notify customer of shipment ----
            await workflow.execute_activity(
                send_notification,
                args=[
                    order.customer_email,
                    f"Order {order.order_id} has shipped!",
                    (
                        f"Your order is on its way via {shipment.carrier}.\n"
                        f"  Tracking: {shipment.tracking_number}\n"
                        f"  Estimated delivery: {shipment.estimated_delivery}"
                    ),
                ],
                start_to_close_timeout=timedelta(seconds=10),
            )

            # ---- Step 8: Wait for admin to confirm delivery ----
            self._update_status(OrderStatus.AWAITING_DELIVERY)
            await self._wait_for_advance(
                lambda: self._delivery_confirmed or self._cancelled,
                "delivery",
            )
            if self._cancelled:
                raise ApplicationError("Order cancelled by operator (before delivery confirmation)")

            self._update_status(OrderStatus.DELIVERED)

            await workflow.execute_activity(
                send_notification,
                args=[
                    order.customer_email,
                    f"Order {order.order_id} delivered!",
                    "Your order has been delivered. Thank you for your purchase!",
                ],
                start_to_close_timeout=timedelta(seconds=10),
            )

            return self._state

        except Exception as exc:
            # ----------------------------------------------------------
            # SAGA COMPENSATION: undo completed steps in reverse order
            # Each step is logged individually so the admin can see the
            # rollback happening step-by-step in the UI.
            # ----------------------------------------------------------
            workflow.logger.warning(
                "Order %s failed: %s -- starting compensation ...",
                order.order_id,
                exc,
            )
            self._state.failure_reason = str(exc)
            self._update_status(OrderStatus.COMPENSATING)

            # --- Compensate shipping ---
            if self._tracking_number:
                await self._run_compensation(
                    "cancel_shipment",
                    cancel_shipment,
                    self._tracking_number,
                )

            # --- Compensate packing ---
            if self._package_label:
                await self._run_compensation(
                    "unpack_order",
                    unpack_order,
                    self._package_label,
                )

            # --- Compensate picking ---
            if self._items_picked:
                await self._run_compensation(
                    "return_items_to_shelf",
                    return_items_to_shelf,
                    order,
                )

            # --- Compensate inventory ---
            if self._reservation_id:
                await self._run_compensation(
                    "release_inventory",
                    release_inventory,
                    self._reservation_id,
                )

            # --- Compensate payment ---
            if self._transaction_id:
                await self._run_compensation_multi(
                    "refund_payment",
                    refund_payment,
                    [order, self._transaction_id],
                )

            self._update_status(OrderStatus.CANCELLED)

            # Notify customer
            await workflow.execute_activity(
                send_notification,
                args=[
                    order.customer_email,
                    f"Order {order.order_id} cancelled",
                    (
                        f"Your order has been cancelled.\n"
                        f"  Reason: {exc}\n"
                        f"  Compensations run: {', '.join(self._state.compensations_run)}"
                    ),
                ],
                start_to_close_timeout=timedelta(seconds=10),
            )

            return self._state

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    @workflow.signal
    async def approve(self) -> None:
        """Approve a high-value order that is awaiting human review."""
        workflow.logger.info("Received APPROVE signal.")
        self._approved = True

    @workflow.signal
    async def cancel(self) -> None:
        """Cancel the order."""
        workflow.logger.info("Received CANCEL signal.")
        self._cancelled = True

    @workflow.signal
    async def advance_to_pick(self) -> None:
        """Admin confirms: start warehouse picking."""
        workflow.logger.info("Received ADVANCE_TO_PICK signal.")
        self._pick_requested = True

    @workflow.signal
    async def advance_to_pack(self) -> None:
        """Admin confirms: start packing."""
        workflow.logger.info("Received ADVANCE_TO_PACK signal.")
        self._pack_requested = True

    @workflow.signal
    async def advance_to_ship(self) -> None:
        """Admin confirms: ship the order."""
        workflow.logger.info("Received ADVANCE_TO_SHIP signal.")
        self._ship_requested = True

    @workflow.signal
    async def confirm_delivery(self) -> None:
        """Admin confirms: order has been delivered."""
        workflow.logger.info("Received CONFIRM_DELIVERY signal.")
        self._delivery_confirmed = True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @workflow.query
    def get_status(self) -> OrderState:
        """Return the current order state (callable while the workflow runs)."""
        return self._state

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_status(self, status: OrderStatus) -> None:
        self._state.status = status.value
        self._state.status_history.append(
            (status.value, workflow.now().isoformat())
        )
        workflow.logger.info(
            "Order %s -> %s", self._state.order.order_id, status.value
        )

    async def _wait_for_advance(self, condition, step_name: str) -> None:
        """Wait for an admin signal to advance to the next step."""
        workflow.logger.info(
            "Order %s waiting for admin to advance: %s",
            self._state.order.order_id,
            step_name,
        )
        await workflow.wait_condition(condition)

    async def _run_compensation(self, name: str, activity_fn, arg) -> None:
        """Run a single-arg compensation activity and record it."""
        workflow.logger.info("COMPENSATING: %s ...", name)
        self._state.status_history.append(
            (f"COMPENSATING:{name}", workflow.now().isoformat())
        )
        await workflow.execute_activity(
            activity_fn,
            arg,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_COMPENSATION_RETRY,
        )
        self._state.compensations_run.append(name)
        workflow.logger.info("COMPENSATED: %s", name)

    async def _run_compensation_multi(self, name: str, activity_fn, args: list) -> None:
        """Run a multi-arg compensation activity and record it."""
        workflow.logger.info("COMPENSATING: %s ...", name)
        self._state.status_history.append(
            (f"COMPENSATING:{name}", workflow.now().isoformat())
        )
        await workflow.execute_activity(
            activity_fn,
            args=args,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_COMPENSATION_RETRY,
        )
        self._state.compensations_run.append(name)
        workflow.logger.info("COMPENSATED: %s", name)
