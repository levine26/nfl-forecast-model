from __future__ import annotations

from email.message import Message
import importlib.util
import io
from pathlib import Path
from urllib.error import HTTPError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_groq_media_prompt.py"
spec = importlib.util.spec_from_file_location("run_groq_media_prompt", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _http_error(code: int, *, body: str = "", **headers: str) -> HTTPError:
    message = Message()
    for key, value in headers.items():
        message[key.replace("_", "-")] = value
    fp = io.BytesIO(body.encode("utf-8")) if body else None
    return HTTPError("https://api.groq.com", code, "Provider Error", message, fp)


def _http_429(*, body: str = "", **headers: str) -> HTTPError:
    return _http_error(429, body=body, **headers)


def test_compound_mini_is_default_provider_with_gpt_oss_long_window_fallback():
    assert module.DEFAULT_MODEL == "groq/compound-mini"
    assert module.FALLBACK_MODEL == "openai/gpt-oss-120b"
    assert module.DEFAULT_COMPOUND_VERSION == "2025-07-23"
    assert module.MAX_COMPLETION_TOKENS == 600
    assert module.FALLBACK_MAX_COMPLETION_TOKENS == 2048
    assert module.FALLBACK_TOOL_TEMPERATURES == (0.6, 0.2)


def test_compound_mini_payload_bounds_reserved_output_budget():
    payload = module._build_payload("research this game", model=module.DEFAULT_MODEL)
    assert payload["model"] == "groq/compound-mini"
    assert payload["messages"] == [{"role": "user", "content": "research this game"}]
    assert payload["max_completion_tokens"] == 600
    assert payload["search_settings"]["include_domains"]
    assert set(payload) == {"model", "messages", "max_completion_tokens", "search_settings"}
    for optional in (
        "citation_options",
        "compound_custom",
        "reasoning_effort",
        "reasoning_format",
        "response_format",
        "service_tier",
        "temperature",
        "tool_choice",
        "tools",
        "top_p",
    ):
        assert optional not in payload


def test_gpt_oss_fallback_uses_documented_browser_search_budget_and_controls():
    payload = module._build_payload("research this game", model=module.FALLBACK_MODEL)
    assert payload == {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": "research this game"}],
        "max_completion_tokens": 2048,
        "reasoning_effort": "low",
        "reasoning_format": "hidden",
        "temperature": 0.6,
        "top_p": 0.95,
        "tool_choice": "required",
        "tools": [{"type": "browser_search"}],
    }
    assert "search_settings" not in payload


def test_gpt_oss_fallback_accepts_lower_tool_retry_temperature():
    payload = module._build_payload(
        "research this game",
        model=module.FALLBACK_MODEL,
        tool_temperature=0.2,
    )
    assert payload["temperature"] == 0.2
    assert payload["max_completion_tokens"] == 2048
    assert payload["tool_choice"] == "required"


def test_browser_search_is_recognized_as_web_research():
    used, markers = module._used_web_research(
        {"executed_tools": [{"type": "function", "name": "browser_search"}]}
    )
    assert used is True
    assert "browser_search" in markers


def test_rate_limit_delay_honors_retry_after_seconds():
    exc = _http_429(retry_after="17", x_ratelimit_remaining_tokens="0")
    assert module._rate_limit_delay(exc, 1) == 18.0


def test_rate_limit_delay_fails_closed_on_long_quota_window():
    exc = _http_429(retry_after="600", x_ratelimit_remaining_requests="0")
    assert module._rate_limit_delay(exc, 1) is None


def test_rate_limit_delay_fails_closed_on_tpd_without_retry_after():
    exc = _http_429(
        body='{"error":{"message":"Rate limit reached for model meta-llama/llama-4-scout-17b-16e-instruct: tokens per day exceeded"}}'
    )
    assert module._rate_limit_delay(exc, 1) is None


def test_rate_limit_delay_uses_minute_window_fallback_without_header():
    exc = _http_429()
    assert module._rate_limit_delay(exc, 1) == 20.0
    assert module._rate_limit_delay(exc, 2) == 40.0
    assert module._rate_limit_delay(exc, 3) == 75.0


def test_safe_rate_limit_headers_exposes_only_allowlisted_fields():
    exc = _http_429(
        retry_after="9",
        x_ratelimit_remaining_tokens="123",
        authorization="secret-value",
    )
    headers = module._safe_rate_limit_headers(exc)
    assert headers["retry-after"] == "9"
    assert headers["x-ratelimit-remaining-tokens"] == "123"
    assert "authorization" not in headers


def test_safe_rate_limit_reason_classifies_without_echoing_body():
    exc = _http_429(
        body='{"error":{"message":"Rate limit reached for model openai/gpt-oss-120b: tokens per minute exceeded; prompt secret-do-not-log"}}'
    )
    reason = module._safe_rate_limit_reason(exc)
    assert "tpm" in reason
    assert "model=openai/gpt-oss-120b" in reason
    assert "secret-do-not-log" not in reason


def test_run_switches_compound_tpd_to_gpt_oss_browser_fallback(monkeypatch):
    calls: list[tuple[str, float | None]] = []

    def fake_request(
        prompt: str,
        *,
        model: str,
        timeout: int,
        tool_temperature: float | None = None,
    ) -> str:
        calls.append((model, tool_temperature))
        if len(calls) == 1:
            raise _http_429(
                body='{"error":{"message":"Rate limit reached for model meta-llama/llama-4-scout-17b-16e-instruct: tokens per day exceeded"}}'
            )
        return "accepted researched payload"

    monkeypatch.setattr(module, "_request", fake_request)
    result = module.run("prompt", model=module.DEFAULT_MODEL, timeout=10, attempts=3)
    assert result == "accepted researched payload"
    assert calls == [
        (module.DEFAULT_MODEL, None),
        (module.FALLBACK_MODEL, 0.6),
    ]


def test_run_retries_gpt_oss_tool_use_failure_at_lower_temperature(monkeypatch):
    calls: list[tuple[str, float | None]] = []

    def fake_request(
        prompt: str,
        *,
        model: str,
        timeout: int,
        tool_temperature: float | None = None,
    ) -> str:
        calls.append((model, tool_temperature))
        if len(calls) == 1:
            raise _http_429(
                body='{"error":{"message":"Rate limit reached for model meta-llama/llama-4-scout-17b-16e-instruct: tokens per day exceeded"}}'
            )
        if len(calls) == 2:
            raise _http_error(
                400,
                body='{"error":{"message":"Invalid tool call generated",'
                '"type":"invalid_request_error","code":"tool_use_failed"}}',
            )
        return "accepted researched payload"

    monkeypatch.setattr(module, "_request", fake_request)
    result = module.run("prompt", model=module.DEFAULT_MODEL, timeout=10, attempts=3)
    assert result == "accepted researched payload"
    assert calls == [
        (module.DEFAULT_MODEL, None),
        (module.FALLBACK_MODEL, 0.6),
        (module.FALLBACK_MODEL, 0.2),
    ]


def test_run_does_not_loop_when_fallback_hits_long_window_quota(monkeypatch):
    calls: list[tuple[str, float | None]] = []

    def fake_request(
        prompt: str,
        *,
        model: str,
        timeout: int,
        tool_temperature: float | None = None,
    ) -> str:
        calls.append((model, tool_temperature))
        if model == module.DEFAULT_MODEL:
            raise _http_429(
                body='{"error":{"message":"Rate limit reached for model meta-llama/llama-4-scout-17b-16e-instruct: tokens per day exceeded"}}'
            )
        raise _http_429(
            body='{"error":{"message":"Rate limit reached for model openai/gpt-oss-120b: tokens per day exceeded"}}'
        )

    monkeypatch.setattr(module, "_request", fake_request)
    try:
        module.run("prompt", model=module.DEFAULT_MODEL, timeout=10, attempts=3)
    except RuntimeError as exc:
        assert "tpd" in str(exc)
    else:
        raise AssertionError("expected long-window quota failure")
    assert calls == [
        (module.DEFAULT_MODEL, None),
        (module.FALLBACK_MODEL, 0.6),
    ]


def test_safe_bad_request_reason_exposes_only_allowlisted_diagnostics():
    exc = _http_error(
        400,
        body='{"error":{"message":"Unsupported parameter response_format; prompt secret-do-not-log",'
        '"type":"invalid_request_error","code":"unsupported_parameter","param":"response_format.type"}}',
    )
    reason = module._safe_bad_request_reason(exc)
    assert "param=response_format" in reason
    assert "type=invalid_request_error" in reason
    assert "code=unsupported_parameter" in reason
    assert "response_format" in reason
    assert "secret-do-not-log" not in reason


def test_safe_bad_request_reason_classifies_tool_use_failed_without_failed_generation_leak():
    exc = _http_error(
        400,
        body='{"error":{"message":"Invalid tool call generated",'
        '"type":"invalid_request_error","code":"tool_use_failed",'
        '"failed_generation":{"attempted_arguments":"secret-do-not-log"}}}',
    )
    reason = module._safe_bad_request_reason(exc)
    assert "code=tool_use_failed" in reason
    assert "type=invalid_request_error" in reason
    assert "secret-do-not-log" not in reason


def test_safe_bad_request_reason_does_not_echo_unknown_param_or_message():
    exc = _http_error(
        400,
        body='{"error":{"message":"bad secret-token-123", "param":"private_prompt", "type":"weird type"}}',
    )
    reason = module._safe_bad_request_reason(exc)
    assert reason == "bad_request"
    assert "private_prompt" not in reason
    assert "secret-token-123" not in reason


def test_safe_413_reason_exposes_only_budget_metadata():
    exc = _http_error(
        413,
        body='{"error":{"message":"Request too large for model `openai/gpt-oss-120b` in organization org_secret '
        'on tokens per minute (TPM): Limit 8000, Requested 9174; prompt secret-do-not-log"}}',
    )
    reason = module._safe_request_too_large_reason(exc)
    assert "tpm" in reason
    assert "model=openai/gpt-oss-120b" in reason
    assert "limit=8000" in reason
    assert "requested=9174" in reason
    assert "org_secret" not in reason
    assert "secret-do-not-log" not in reason
