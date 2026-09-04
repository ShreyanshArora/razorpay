"""LLM provider abstraction.

Real reasoning when an API key is present; a deterministic, evidence-grounded
fallback otherwise so the full pipeline and the live demo ALWAYS run. Both paths
return the SAME structured schema, so nothing downstream cares which ran.

Supported (auto-detected via env):
  ANTHROPIC_API_KEY  -> Claude
  OPENAI_API_KEY     -> OpenAI
  (none)             -> RuleBasedInvestigator fallback
"""
from __future__ import annotations
import json, os
from typing import Optional


class LLMUnavailable(Exception):
    pass


def get_provider() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "fallback"


def call_llm(system: str, user: str, provider: Optional[str] = None) -> str:
    provider = provider or get_provider()
    if provider == "anthropic":
        return _call_anthropic(system, user)
    if provider == "openai":
        return _call_openai(system, user)
    raise LLMUnavailable("no API key configured")


def _call_anthropic(system: str, user: str) -> str:
    import urllib.request
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": os.environ.get("NEXUS_MODEL", "claude-3-5-sonnet-20241022"),
            "max_tokens": 1200, "system": system,
            "messages": [{"role": "user", "content": user}],
        }).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read())
    return data["content"][0]["text"]


def _call_openai(system: str, user: str) -> str:
    import urllib.request
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": os.environ.get("NEXUS_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": 1200,
        }).encode(),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]
