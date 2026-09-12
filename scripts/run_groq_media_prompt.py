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
# Groq documents 2025-07-23 as the basic-search Compound version. Advanced search
# retrieves more context; basic search is intentionally used here to stay inside the
# tighter Free-tier limits inherited from Compound Mini's underlying models.
DEFAULT_COMPOUND_VERSION = "2025-07-23"
# Keep the reserved generation budget far below the 8K TPM ceiling of the routed
# GPT-OSS model on Groq Free tier. The focused JSON contract is comfortably smaller.
MAX_COMPLETION_TOKENS = 600
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
_SAFE_ERROR_PARAMS = {
    "citation_options",
    "compound_custom",
    "max_completion_tokens",
    "messages",
    "model",
    "reasoning_format",
    "response_format",
    "search_settings",
    "service_tier",
    "temperature",
    "tools",
}
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


def _error_payload(exc: HTTPError) -> dict:
    """Read a provider error body for classification only; callers never log it."""
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(raw)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _error_message(payload: dict) -> str:
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    return str(error.get("message") or "")


def _safe_rate_limit_reason(exc: HTTPError) -> str:
    """Classify a Groq 429 without logging the raw provider response body."""
    payload = _error_payload(exc)
    lowered = _error_message(payload).lower()
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
    model_match = re.search(r"\bmodel\s+[`'\"]?([a-z0-9_.\-/]+)", lowered)
    model = model_match.group(1) if model_match else ""
    parts = kinds or ["rate_limit"]
    if model and len(model) <= 80:
        parts.append(f"model={model}")
    return ",".join(parts)


def _safe_bad_request_reason(exc: HTTPError) -> str:
    """Classify a 400 without echoing arbitrary provider text or request content."""
    payload = _error_payload(exc)
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    message = str(error.get("message") or "").lower()
    parts: list[str] = []

    for field in ("param", "type", "code"):
        value = str(error.get(field) or "").strip().lower()
        if not value:
            continue
        if field == "param":
            root = value.split(".", 1)[0].split("[", 1)[0]
            if root in _SAFE_ERROR_PARAMS:
                parts.append(f"param={root}")
        elif re.fullmatch(r"[a-z0-9_.-]{1,80}", value):
            parts.append(f"{field}={value}")

    for token, label in (
        ("response_format", "response_format"),
        ("reasoning_format", "reasoning_format"),
        ("compound_custom", "compound_custom"),
        ("search_settings", "search_settings"),
        ("citation_options", "citation_options"),
        ("service_tier", "service_tier"),
        ("max_completion_tokens", "max_completion_tokens"),
        ("temperature", "temperature"),
        ("invalid", "invalid_request"),
        ("unsupported", "unsupported_parameter"),
    ):
        if token in message and label not in parts:
            parts.append(label)

    return ",".join(parts) if parts else "bad_request"


def _safe_request_too_large_reason(exc: HTTPError) -> str:
    """Classify a 413 using only model/limit/requested token-budget metadata."""
    payload = _error_payload(exc)
    message = _error_message(payload).lower()
    parts: list[str] = []
    if "tokens per minute" in message or "tpm" in message:
        parts.append("tpm")
    elif "token" in message:
        parts.append("token_budget")
    else:
        parts.append("request_too_large")

    model_match = re.search(r"\bmodel\s+[`'\"]?([a-z0-9_.\-/]+)", message)
    if model_match:
        model = model_match.group(1)
        if len(model) <= 80:
            parts.append(f"model={model}")

    for label, pattern in (
        ("limit", r"\blimit\s*[:=]?\s*([0-9][0-9,]*)"),
        ("requested", r"\brequested\s*[:=]?\s*([0-9][0-9,]*)"),
    ):
        match = re.search(pattern, message)
        if match:
            parts.append(f"{label}={match.group(1).replace(',', '')}")
    return ",".join(parts)


def _rate_limit_delay(exc: HTTPError, attempt: int) -> float | None:
    retry_after = _parse_retry_after(_safe_rate_limit_headers(exc).get("retry-after"))
    if retry_after is not None:
        if retry_after > MAX_RATE_LIMIT_WAIT_SECONDS:
            return None
        return max(1.0, retry_after + 1.0)
    return min(20.0 * (2 ** max(0, attempt - 1)), 75.0)


def _build_payload(prompt: str, *, model: str) -> dict:
    """Keep the Mini request simple while explicitly bounding reserved output tokens."""
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "search_settings": {
            "include_domains": sorted(APPROVED_MEDIA_DOMAINS),
        },
    }


def _request(prompt: str, *, model: str, timeout: int) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    compound_version = os.environ.get("GROQ_COMPOUND_VERSION", DEFAULT_COMPOUND_VERSION).strip() or DEFAULT_COMPOUND_VERSION
    request = Request(
        API_URL,
        data=json.dumps(_build_payload(prompt, model=model)).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Groq-Model-Version": compound_version,
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

            if exc.code == 400:
                reason = _safe_bad_request_reason(exc)
                print(f"Groq HTTP 400 bad request class={reason}", file=sys.stderr)
                last_error = RuntimeError(f"Groq HTTP 400 class={reason}")
                break

            if exc.code == 413:
                reason = _safe_request_too_large_reason(exc)
                print(f"Groq HTTP 413 request too large class={reason}", file=sys.stderr)
                last_error = RuntimeError(f"Groq HTTP 413 class={reason}")
                break

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
