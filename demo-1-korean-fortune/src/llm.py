"""LLM provider abstraction for the fortune activity.

Supports three providers, selected via the ``FORTUNE_PROVIDER`` env var:

  * ``openai`` -- call the OpenAI API (requires ``OPENAI_API_KEY``)
  * ``claude`` -- shell out to the local Claude Code CLI (``claude -p``)
  * ``cursor`` -- shell out to the local Cursor CLI (``agent -p``)

"Local-AI mode" simply means picking one of the CLI providers so the demo
runs with no API key -- just a coding agent you already have installed.

When ``FORTUNE_PROVIDER`` is unset the provider is auto-selected:
  * if ``OPENAI_API_KEY`` is set          -> ``openai``
  * otherwise (local-AI mode by default)  -> ``claude``

Binaries are configurable via ``CLAUDE_CLI_BIN`` (default ``claude``) and
``CURSOR_CLI_BIN`` (default ``agent``), and the CLI timeout via
``LOCAL_AI_TIMEOUT`` (default 90 seconds).
"""

from __future__ import annotations

import asyncio
import json
import os

OPENAI = "openai"
CLAUDE = "claude"
CURSOR = "cursor"

VALID_PROVIDERS = (OPENAI, CLAUDE, CURSOR)


class LLMError(RuntimeError):
    """Raised when a provider cannot produce a completion."""


def resolve_provider() -> str:
    """Return the active provider name based on the environment.

    Explicit ``FORTUNE_PROVIDER`` wins; otherwise fall back to OpenAI when a
    key is present and to the local Claude CLI when it is not.
    """
    explicit = os.environ.get("FORTUNE_PROVIDER", "").strip().lower()
    if explicit:
        if explicit not in VALID_PROVIDERS:
            raise LLMError(
                f"Unknown FORTUNE_PROVIDER={explicit!r}; "
                f"expected one of {', '.join(VALID_PROVIDERS)}"
            )
        return explicit

    if os.environ.get("OPENAI_API_KEY"):
        return OPENAI
    return CLAUDE


def describe_provider() -> str:
    """Human-readable description of the active provider (for banners/logs)."""
    provider = resolve_provider()
    if provider == OPENAI:
        return "OpenAI API"
    if provider == CLAUDE:
        return f"Claude Code CLI ({os.environ.get('CLAUDE_CLI_BIN', 'claude')})"
    return f"Cursor CLI ({os.environ.get('CURSOR_CLI_BIN', 'agent')})"


def extract_json(text: str) -> dict:
    """Extract the first JSON object from a model/CLI response.

    Coding-agent CLIs sometimes wrap the JSON in markdown fences or add a line
    of commentary, so we locate the outermost ``{...}`` rather than assuming
    the whole response is clean JSON.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Drop the opening fence (``` or ```json) and a trailing fence if present.
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMError(f"No JSON object found in response: {text[:200]!r}")

    return json.loads(cleaned[start : end + 1])


async def _run_cli(argv: list[str], prompt: str) -> str:
    """Run a local coding-agent CLI, feeding the prompt on stdin."""
    timeout = float(os.environ.get("LOCAL_AI_TIMEOUT", "90"))
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise LLMError(
            f"CLI '{argv[0]}' not found on PATH. Install it or set the "
            f"matching *_CLI_BIN env var."
        ) from exc

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(prompt.encode()), timeout=timeout
        )
    except asyncio.TimeoutError as exc:
        proc.kill()
        raise LLMError(f"CLI '{argv[0]}' timed out after {timeout:.0f}s") from exc

    if proc.returncode != 0:
        raise LLMError(
            f"CLI '{argv[0]}' exited with code {proc.returncode}: "
            f"{stderr.decode(errors='replace').strip()[:300]}"
        )

    return stdout.decode(errors="replace").strip()


async def _complete_openai(prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY is not set")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    def _call() -> str:
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-5.5"),
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    # The OpenAI SDK call is synchronous; keep the event loop free.
    return await asyncio.to_thread(_call)


async def _complete_claude(prompt: str) -> str:
    bin_name = os.environ.get("CLAUDE_CLI_BIN", "claude")
    # `claude -p` (print mode) runs headless and prints the final text reply.
    return await _run_cli([bin_name, "-p"], prompt)


async def _complete_cursor(prompt: str) -> str:
    bin_name = os.environ.get("CURSOR_CLI_BIN", "agent")
    # `agent -p` (print mode) with plain-text output.
    return await _run_cli([bin_name, "-p", "--output-format", "text"], prompt)


async def generate_completion(prompt: str) -> str:
    """Generate a completion from the active provider. Raises ``LLMError``."""
    provider = resolve_provider()
    if provider == OPENAI:
        return await _complete_openai(prompt)
    if provider == CLAUDE:
        return await _complete_claude(prompt)
    return await _complete_cursor(prompt)
