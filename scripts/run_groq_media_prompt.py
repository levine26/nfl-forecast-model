from __future__ import annotations

"""Run one Sunday Signal editorial research prompt through Groq.

This module is intentionally provider-only. It does not alter LevLine predictions,
locks, grading, or publication semantics. The existing deterministic validators
remain authoritative for whether generated editorial prose is publishable.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from nfl_forecast.source_policy import APPROVED_MEDIA_DOMAINS

API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Compound Mini is deliberate for the current Free-tier production key: it uses at
# most one tool call, avoiding the hidden underlying-model TPM amplification that
# full Compound can incur during a multi-search agentic loop.
DEFAULT_MODEL = "groq/compound-mini"
_WEB_TOOL_TYPES = {"search", "web_search"}
_RATE_LIMIT_HEADER_NAMES = (
    "retry-after",
    "x-ratelimit-limit-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-requests",
    "x-ratelimit-reset-tokens",
)
MAX_RATE_LIMIT_WAIT_SECONDS = 180.0


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return seconds


def _safe_rate_limit_headers(exc: HTTPError) -> dict[str, str]:
    headers = getattr(exc, "headers", None)
    if headers is None:
        return {}
    safe: dict[str, str] = {}
    for name in _RATE_LIMIT_HEADER_NAMES:
        value = headers.get(name)
        if value is not None:
            safe[name] = str(value).strip()
    return safe


def _safe_rate_limit_reason(exc: HTTPError) -> str:
    """Classify a Groq 429 without logging the raw provider response body."""
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(raw)
        message = str((payload.get("error") or {}).get("message") or "")
    except Exception:
        return "unclassified"

    lowered = message.lower()
    kinds: list[str] = []
    for token, label in (
        ("input tokens per minute", "itpm"),
        ("output tokens per minute", "otpm"),
        ("tokens per minute", "tpm"),
        ("requests per minute", "rpm"),
        ("requests per day", "rpd"),
        ("tokens per day", "tpd"),
        ("project", "project_limit"),
        ("capacity", "capacity"),
    ):
        if token in lowered and label not in kinds:
            kinds.append(label)
    model_match = re.search(r"(?:model|for)\s+[`'\"]?([a-z0-9_.\-/]+)", lowered)
    model = model_match.group(1) if model_match else ""
    parts = kinds or ["rate_limit"]
    if model and len(model) <= 80:
        parts.append(f"model={model}")
    return ",".join(parts)


def _rate_limit_delay(exc: HTTPError, attempt: int) -> float | None:
    retry_after = _parse_retry_after(_safe_rate_limit_headers(exc).get("retry-after"))
    if retry_after is not None:
        if retry_after > MAX_RATE_LIMIT_WAIT_SECONDS:
            return None
        return max(1.0, retry_after + 1.0)
    return min(20.0 * (2 ** max(0, attempt - 1)), 75.0)


def _request(prompt: str, *, model: str, timeout: int) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    payload = {
        "model": model,
        "service_tier": "auto",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_completion_tokens": 1200,
        "response_format": {"type": "json_object"},
        "citation_options": "disabled",
        "search_settings": {
            "include_domains": sorted(APPROVED_MEDIA_DOMAINS),
        },
        "compound_custom": {
            "tools": {
                # One broad search can return multiple publisher results. Restricting
                # Mini to web_search guarantees its single tool call is spent on fresh
                # reporting rather than an unnecessary secondary tool.
                "enabled_tools": ["web_search"],
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
        raise RuntimeError("Groq response used no web-search tool")

    print("Groq research tools used:", ", ".join(sorted(tool_types & _WEB_TOOL_TYPES)))
    return content


def run(prompt: str, *, model: str, timeout: int, attempts: int) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _request(prompt, model=model, timeout=timeout)
        except HTTPError as exc:
            retryable = exc.code in {408, 409, 429, 498, 500, 502, 503, 504}
            if exc.code == 429:
                safe_headers = _safe_rate_limit_headers(exc)
                reason = _safe_rate_limit_reason(exc)
                detail = ", ".join(f"{key}={value}" for key, value in safe_headers.items()) or "no rate-limit headers"
                print(f"Groq HTTP 429 rate limit class={reason} ({detail})", file=sys.stderr)
                delay = _rate_limit_delay(exc, attempt)
                last_error = RuntimeError(f"Groq HTTP 429 class={reason} ({detail})")
                if attempt == attempts or delay is None:
                    break
                print(f"Groq rate-limited; waiting {delay:.1f}s before provider retry {attempt + 1}/{attempts}.", file=sys.stderr)
                time.sleep(delay)
                continue

            last_error = RuntimeError(f"Groq HTTP {exc.code}")
            if not retryable or attempt == attempts:
                break
            time.sleep(min(2 ** attempt, 8))
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
