import os

from temporalio.client import Client


# Connection settings are read from the environment so the same code works
# against a local `temporal server start-dev` instance or Temporal Cloud.
#
#   TEMPORAL_ADDRESS    host:port of the Temporal frontend
#                       (default: localhost:7233 for the local dev server)
#   TEMPORAL_NAMESPACE  namespace to use (default: "default", which the
#                       local dev server creates automatically)
#   TEMPORAL_API_KEY    Temporal Cloud API key. When set, the client connects
#                       with TLS + API-key auth (Cloud). When unset, it makes
#                       a plaintext connection suitable for the local server.
DEFAULT_ADDRESS = "localhost:7233"
DEFAULT_NAMESPACE = "default"


async def get_client() -> Client:
    """Connect to Temporal (local dev server or Temporal Cloud).

    Selection is driven by environment variables:
      * If TEMPORAL_API_KEY is set, connect to Temporal Cloud (TLS + API key).
      * Otherwise, connect to a local server over plaintext.
    """
    address = os.environ.get("TEMPORAL_ADDRESS", DEFAULT_ADDRESS)
    namespace = os.environ.get("TEMPORAL_NAMESPACE", DEFAULT_NAMESPACE)
    api_key = os.environ.get("TEMPORAL_API_KEY")

    if api_key:
        # Temporal Cloud: TLS + API-key authentication.
        return await Client.connect(
            address,
            namespace=namespace,
            api_key=api_key,
            tls=True,
        )

    # Local dev server (`temporal server start-dev`): plaintext connection.
    return await Client.connect(address, namespace=namespace)
