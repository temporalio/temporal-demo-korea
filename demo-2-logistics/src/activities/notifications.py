"""Notification activities (simulated email / SMS)."""

from __future__ import annotations

import asyncio

from temporalio import activity


@activity.defn
async def send_notification(customer_email: str, subject: str, message: str) -> bool:
    """Simulate sending an email or SMS notification.

    In production this would call an email API; here we just print to the console.
    """
    activity.logger.info("Sending notification to %s ...", customer_email)
    await asyncio.sleep(0.2)

    border = "=" * 60
    print(
        f"\n{border}\n"
        f"  NOTIFICATION\n"
        f"  To:      {customer_email}\n"
        f"  Subject: {subject}\n"
        f"{'-' * 60}\n"
        f"  {message}\n"
        f"{border}\n"
    )
    return True
