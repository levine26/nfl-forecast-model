from __future__ import annotations

from email.message import Message
from urllib.error import HTTPError

from scripts.run_groq_media_prompt import _duration_seconds, _rate_limit_delay


def _http_429(headers: dict[str, str]) -> HTTPError:
    message = Message()
    for key, value in headers.items():
        message[key] = value
    return HTTPError(
        url="https://api.groq.com/openai/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs=message,
        fp=None,
    )


def test_duration_seconds_parses_groq_reset_formats() -> None:
    assert _duration_seconds("2") == 2.0
    assert _duration_seconds("7.66s") == 7.66
    assert _duration_seconds("2m59.56s") == 179.56
    assert _duration_seconds("") is None
    assert _duration_seconds("n/a") is None


def test_rate_limit_delay_prefers_retry_after() -> None:
    exc = _http_429(
        {
            "retry-after": "11",
            "x-ratelimit-reset-tokens": "3s",
            "x-ratelimit-reset-requests": "2m",
        }
    )
    assert _rate_limit_delay(exc) == 12.0


def test_rate_limit_delay_uses_shortest_reset_when_retry_after_missing() -> None:
    exc = _http_429(
        {
            "x-ratelimit-reset-tokens": "7.66s",
            "x-ratelimit-reset-requests": "2m59.56s",
        }
    )
    assert _rate_limit_delay(exc) == 8.66


def test_rate_limit_delay_has_safe_default_and_cap() -> None:
    assert _rate_limit_delay(_http_429({})) == 30.0
    assert _rate_limit_delay(_http_429({"retry-after": "900"})) == 300.0
