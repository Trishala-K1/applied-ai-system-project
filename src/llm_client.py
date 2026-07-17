"""
Thin wrapper around the Anthropic API so agent.py doesn't touch the SDK directly.
Requires ANTHROPIC_API_KEY to be set in the environment.
"""
import os

from anthropic import Anthropic

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")

_client = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it before running the agent, "
                "e.g. `export ANTHROPIC_API_KEY=sk-ant-...`"
            )
        _client = Anthropic(api_key=api_key)
    return _client


def call_llm(system: str, user: str, max_tokens: int = 500) -> str:
    """Sends one message to the LLM and returns the raw text response."""
    client = get_client()
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text
