from scripts.groq_quota_circuit import shared_long_window_quota_exhausted as exhausted


def test_stops_on_verified_shared_daily_token_quota():
    assert exhausted("Groq HTTP 429 rate limit class=tpd,model=openai/gpt-oss-120b (retry-after=851)")
    assert exhausted("Groq HTTP 429 class=rpd (retry-after=2400)")
    assert exhausted("Groq HTTP 429 class=tpm,tpd (retry-after=1000)")


def test_does_not_stop_on_transient_quota_or_unrelated_failures():
    for sample in (
        "Groq HTTP 429 class=tpm (retry-after=60)",
        "Groq HTTP 429 class=rpm (retry-after=15)",
        "Groq HTTP 500 class=tpd",
        "Invalid tool call generated",
        "provider retrieval timed out",
        "",
        "Groq HTTP 429 class=capacity",
    ):
        assert not exhausted(sample), sample


def test_scanner_cannot_be_fooled_by_ordinary_quote_of_daily_quota():
    assert not exhausted("Article title: Groq exceeds tokens per day for Sunday Signal")
    assert not exhausted("Groq HTTP 429 class=tpm; the reporter mentioned tpd later elsewhere.")
