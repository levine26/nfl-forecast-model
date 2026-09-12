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

from nfl_forecast.editorial_provider_fallback import recover_focused_payload
from nfl_forecast.source_policy import APPROVED_MEDIA_DOMAINS

API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Compound Mini remains the primary provider because it gives Sunday Signal one
# bounded web-search tool call per matchup. If Compound's hidden underlying model
# exhausts a long-window quota, the runner can fail over to Groq's directly hosted
# GPT-OSS model with its required browser-search tool without changing any LevLine
# model or publication semantics.
DEFAULT_MODEL = "groq/compound-mini"
FALLBACK_MODEL = "openai/gpt-oss-120b"
# Groq documents 2025-07-23 as the basic-search Compound version. Advanced search
# retrieves more context; basic search is intentionally used here to stay inside the
# tighter Free-tier limits inherited from Compound Mini's underlying models.
DEFAULT_COMPOUND_VERSION = "2025-07-23"
# Compound Mini needs a tight budget to stay within the routed Free-tier model's
# minute window. Groq's browser-search quick start reserves 2K output tokens for
# GPT-OSS; the fallback gets that larger budget because tool reasoning consumes part
# of the completion allowance before the final compact JSON is emitted.
MAX_COMPLETION_TOKENS = 600
FALLBACK_MAX_COMPLETION_TOKENS = 2048
FALLBACK_TOOL_TEMPERATURES = (0.6, 0.2)
_WEB_TOOL_TYPES = {"search", "web_search", "browser_search"}
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
    "reasoning_effort",
    "reasoning_format",
    "response_format",
    "search_settings",
    "service_tier",
    "temperature",
    "tool_choice",
    "tools",
    "top_p",
}
MAX_RATE_LIMIT_WAIT_SECONDS = 180.0
_LONG_WINDOW_QUOTA_CLASSES = {"tpd", "rpd"}


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
        ("reasoning_effort", "reasoning_effort"),
        ("compound_custom", "compound_custom"),
        ("search_settings", "search_settings"),
        ("citation_options", "citation_options"),
        ("service_tier", "service_tier"),
        ("max_completion_tokens", "max_completion_tokens"),
        ("temperature", "temperature"),
        ("tool_choice", "tool_choice"),
        ("tools", "tools"),
        ("top_p", "top_p"),
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


def _rate_limit_classes(reason: str) -> set[str]:
    return {part for part in str(reason).split(",") if part and not part.startswith("model=")}


def _rate_limit_delay(exc: HTTPError, attempt: int, *, reason: str | None = None) -> float | None:
    quota_classes = _rate_limit_classes(reason if reason is not None else _safe_rate_limit_reason(exc))
    if quota_classes & (_LONG_WINDOW_QUOTA_CLASSES | {"project_limit"}):
        return None

    retry_after = _parse_retry_after(_safe_rate_limit_headers(exc).get("retry-after"))
    if retry_after is not None:
        if retry_after > MAX_RATE_LIMIT_WAIT_SECONDS:
            return None
        return max(1.0, retry_after + 1.0)
    return min(20.0 * (2 ** max(0, attempt - 1)), 75.0)


def _is_compound_model(model: str) -> bool:
    return model.startswith("groq/compound")


def _is_gpt_oss_model(model: str) -> bool:
    return model.startswith("openai/gpt-oss")


def _fallback_temperature(tool_failure_count: int) -> float:
    index = min(max(0, int(tool_failure_count)), len(FALLBACK_TOOL_TEMPERATURES) - 1)
    return FALLBACK_TOOL_TEMPERATURES[index]


def _build_payload(prompt: str, *, model: str, tool_temperature: float | None = None) -> dict:
    """Build one bounded research request for the configured Groq provider."""
    if _is_gpt_oss_model(model):
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": FALLBACK_MAX_COMPLETION_TOKENS,
            "reasoning_effort": "low",
            "reasoning_format": "hidden",
            "temperature": _fallback_temperature(0) if tool_temperature is None else float(tool_temperature),
            "top_p": 0.95,
            "tool_choice": "required",
            "tools": [{"type": "browser_search"}],
        }
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "search_settings": {
            "include_domains": sorted(APPROVED_MEDIA_DOMAINS),
        },
    }


def _used_web_research(message: dict) -> tuple[bool, set[str]]:
    executed_tools = message.get("executed_tools") or []
    markers: set[str] = set()
    for tool in executed_tools:
        if not isinstance(tool, dict):
            continue
        for key in ("type", "name"):
            value = str(tool.get(key) or "").strip().lower()
            if value:
                markers.add(value)
        if tool.get("search_results"):
            markers.add("browser_search")
    used = any(marker in _WEB_TOOL_TYPES or "search" in marker for marker in markers)
    return used, markers


def _request(prompt: str, *, model: str, timeout: int, tool_temperature: float | None = None) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Sunday-Signal-LevLine/3.0",
    }
    if _is_compound_model(model):
        compound_version = os.environ.get("GROQ_COMPOUND_VERSION", DEFAULT_COMPOUND_VERSION).strip() or DEFAULT_COMPOUND_VERSION
        headers["Groq-Model-Version"] = compound_version

    request = Request(
        API_URL,
        data=json.dumps(_build_payload(prompt, model=model, tool_temperature=tool_temperature)).encode("utf-8"),
        headers=headers,
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

    used_web, tool_markers = _used_web_research(message)
    if not used_web:
        raise RuntimeError("Groq response used no web-search tool")

    visible_tools = sorted(marker for marker in tool_markers if marker in _WEB_TOOL_TYPES or "search" in marker)
    print("Groq research tools used:", ", ".join(visible_tools) or "search")
    return content


def run(prompt: str, *, model: str, timeout: int, attempts: int) -> str:
    last_error: Exception | None = None
    active_model = model
    fallback_tool_failures = 0
    for attempt in range(1, attempts + 1):
        try:
            tool_temperature = _fallback_temperature(fallback_tool_failures) if _is_gpt_oss_model(active_model) else None
            return _request(
                prompt,
                model=active_model,
                timeout=timeout,
                tool_temperature=tool_temperature,
            )
        except HTTPError as exc:
            retryable = exc.code in {408, 409, 429, 498, 500, 502, 503, 504}
            if exc.code == 429:
                safe_headers = _safe_rate_limit_headers(exc)
                reason = _safe_rate_limit_reason(exc)
                detail = ", ".join(f"{key}={value}" for key, value in safe_headers.items()) or "no rate-limit headers"
                print(f"Groq HTTP 429 rate limit class={reason} ({detail})", file=sys.stderr)
                last_error = RuntimeError(f"Groq HTTP 429 class={reason} ({detail})")

                quota_classes = _rate_limit_classes(reason)
                if quota_classes & _LONG_WINDOW_QUOTA_CLASSES and active_model != FALLBACK_MODEL:
                    active_model = os.environ.get("GROQ_MEDIA_FALLBACK_MODEL", FALLBACK_MODEL).strip() or FALLBACK_MODEL
                    fallback_tool_failures = 0
                    print(
                        f"Groq long-window quota reached; switching provider retry to {active_model} with required browser search.",
                        file=sys.stderr,
                    )
                    if attempt == attempts:
                        break
                    continue

                delay = _rate_limit_delay(exc, attempt, reason=reason)
                if attempt == attempts or delay is None:
                    break
                print(f"Groq rate-limited; waiting {delay:.1f}s before provider retry {attempt + 1}/{attempts}.", file=sys.stderr)
                time.sleep(delay)
                continue

            if exc.code == 400:
                reason = _safe_bad_request_reason(exc)
                print(f"Groq HTTP 400 bad request class={reason}", file=sys.stderr)
                last_error = RuntimeError(f"Groq HTTP 400 class={reason}")
                if (
                    _is_gpt_oss_model(active_model)
                    and "code=tool_use_failed" in reason
                    and attempt < attempts
                ):
                    fallback_tool_failures += 1
                    next_temperature = _fallback_temperature(fallback_tool_failures)
                    print(
                        "Groq browser-search tool call was malformed; retrying GPT-OSS "
                        f"with lower temperature {next_temperature:.1f}.",
                        file=sys.stderr,
                    )
                    continue
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
    output_path = Path(args.output_file)
    try:
        content = run(prompt, model=args.model, timeout=args.timeout, attempts=args.attempts)
    except RuntimeError as exc:
        game_id = output_path.stem
        recovered, source = recover_focused_payload(
            game_id=game_id,
            output_path=output_path,
            reason=str(exc),
        )
        if recovered:
            print(
                f"{game_id}: Groq request failed; recovered only this game through {source}. "
                "The focused and full-slate validators remain authoritative.",
                file=sys.stderr,
            )
            return
        raise

    output_path.write_text(content + "\n", encoding="utf-8")
    print(f"Groq editorial response written with primary model {args.model}")


if __name__ == "__main__":
    main()
