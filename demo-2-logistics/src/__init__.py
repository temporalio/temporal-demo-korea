import os

from temporalio.client import Client


TEMPORAL_ADDRESS = "pauloh-june-2026-kr-demo.a2dd6.tmprl.cloud:7233"
TEMPORAL_NAMESPACE = "pauloh-june-2026-kr-demo.a2dd6"


async def get_client() -> Client:
    """Connect to Temporal Cloud."""
    return await Client.connect(
        TEMPORAL_ADDRESS,
        namespace=TEMPORAL_NAMESPACE,
        api_key=os.environ["TEMPORAL_API_KEY"],
        tls=True,
    )
