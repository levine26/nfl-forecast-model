from __future__ import annotations

"""Run one Sunday Signal editorial research prompt through Groq Compound.

This module is intentionally provider-only. It does not alter LevLine predictions,
locks, grading, or publication semantics. The existing deterministic validators
remain authoritative for whether generated editorial prose is publishable.
"""

import argparse
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from nfl_forecast.source_policy import APPROVED_MEDIA_DOMAINS

API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "groq/compound"
_WEB_TOOL_TYPES = {"search", "visit", "web_search", "visit_website"}


def _request(prompt: str, *, model: str, timeout: int) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.35,
        "response_format": {"type": "json_object"},
        # We require explicit source URLs in the JSON payload and validate them ourselves;
        # disabling automatic citation markers keeps user-facing prose clean.
        "citation_options": "disabled",
        "search_settings": {
            "include_domains": sorted(APPROVED_MEDIA_DOMAINS),
        },
        "compound_custom": {
            "tools": {
                "enabled_tools": ["web_search", "visit_website"],
            }
        },
    }
    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Groq-Model-Version": "latest",
            "User-Agent": "Sunday-Signal-LevLine/3.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    body = json.loads(raw)
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("Groq response contained no choices")

    message = (choices[0] or {}).get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise RuntimeError("Groq response contained no message content")

    executed_tools = message.get("executed_tools") or []
    tool_types = {
        str(tool.get("type") or "").strip().lower()
        for tool in executed_tools
        if isinstance(tool, dict)
    }
    if not (tool_types & _WEB_TOOL_TYPES):
        raise RuntimeError("Groq response used no web-search or website-visit tool")

    print("Groq research tools used:", ", ".join(sorted(tool_types & _WEB_TOOL_TYPES)))
    return content


def run(prompt: str, *, model: str, timeout: int, attempts: int) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _request(prompt, model=model, timeout=timeout)
        except HTTPError as exc:
            # Never print response bodies: provider errors may echo request metadata.
            last_error = RuntimeError(f"Groq HTTP {exc.code}")
            retryable = exc.code in {408, 409, 429, 500, 502, 503, 504}
            if not retryable or attempt == attempts:
                break
        except (URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == attempts:
                break
        time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Groq media request failed after {attempts} attempts: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--model", default=os.environ.get("GROQ_MEDIA_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()

    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    content = run(prompt, model=args.model, timeout=args.timeout, attempts=args.attempts)
    Path(args.output_file).write_text(content + "\n", encoding="utf-8")
    print(f"Groq editorial response written with {args.model}")


if __name__ == "__main__":
    main()
