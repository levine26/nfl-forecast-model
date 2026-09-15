from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path

import pytest

from research import v09b_nfl_transaction_no_header_source_shape_v6 as m

CONTRACT = Path("research/availability/v09b_nfl_transaction_no_header_source_shape_v6_contract.json")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_fixed_request_universe_is_exactly_72_observed_v5_failures():
    c = _contract()
    rows = c["scope"]["fixed_requests"]
    assert len(rows) == c["scope"]["fixed_request_count"] == 72
    assert len({row["case_id"] for row in rows}) == 72
    assert Counter(row["kind"] for row in rows) == {"initial": 70, "post_pagination": 2}
    assert Counter(row["category"] for row in rows) == {
        "other": 30,
        "trades": 23,
        "terminations": 14,
        "reserve-list": 3,
        "waivers": 2,
    }
    assert Counter(row["month"] for row in rows) == {
        1: 11,
        2: 8,
        3: 4,
        4: 6,
        5: 8,
        6: 8,
        7: 7,
        8: 3,
        10: 1,
        11: 6,
        12: 10,
    }
    assert all(row["month"] != 9 for row in rows)


def test_two_post_pagination_urls_are_frozen_verbatim():
    rows = [r for r in _contract()["scope"]["fixed_requests"] if r["kind"] == "post_pagination"]
    assert {(r["requested_url"], r["accepted_pages_before_v5_failure"]) for r in rows} == {
        (
            "https://amp.nfl.com/transactions/league/waivers/2017/5?after=AAAH4QAAAAUAAAABAAAAAAAKlXA%3D",
            12,
        ),
        (
            "https://amp.nfl.com/transactions/league/waivers/2020/10?after=AAAH5AAAAAoAAAABAAAAAAAMEQ8%3D",
            4,
        ),
    }


def test_contract_explicitly_forbids_empty_or_terminal_semantics():
    c = _contract()
    assert c["capture"]["preserve_response_body_before_parse"] is True
    assert c["capture"]["no_response_is_classified_as_empty_or_terminal_by_v6"] is True
    assert c["frozen_diagnostic_gate"]["no_empty_semantics_qualification"] is True
    a = c["explicit_non_authority"]
    assert a["empty_result_semantics_qualified"] is False
    assert a["terminal_page_semantics_qualified"] is False
    assert a["all_month_full_ledger_qualified"] is False
    assert a["modern_game_day_roster_universe_qualified"] is False
    assert a["training_label_semantics_qualified"] is False
    assert a["training_source_chronology_qualified"] is False
    assert a["v09b_model_fit_authorized"] is False


def test_raw_capture_is_deterministic_and_exact(tmp_path):
    raw = b"first-party response with no transaction table\n"
    a = tmp_path / "a.html.gz"
    b = tmp_path / "b.html.gz"
    ra = m._write_raw(raw, a)
    rb = m._write_raw(raw, b)
    assert a.read_bytes() == b.read_bytes()
    assert gzip.decompress(a.read_bytes()) == raw
    assert ra["raw_sha256"] == rb["raw_sha256"] == m._sha(raw)
    assert ra["gzip_roundtrip_matches"] is True


def test_visible_text_normalization_is_deterministic_and_excludes_script_style():
    html = "<html><head><style>x</style><script>y</script></head><body><h1>A   B</h1><p>C\nD</p></body></html>"
    assert m._normalize_visible_text(html) == "A B C D"


def test_validate_final_allows_only_https_allowed_host_and_same_path():
    requested = "https://amp.nfl.com/transactions/league/other/2019/4"
    allowed = {"amp.nfl.com", "www.nfl.com"}
    m._validate_final(requested, requested, allowed)
    m._validate_final(requested, "https://www.nfl.com/transactions/league/other/2019/4", allowed)
    with pytest.raises(ValueError):
        m._validate_final(requested, "http://amp.nfl.com/transactions/league/other/2019/4", allowed)
    with pytest.raises(ValueError):
        m._validate_final(requested, "https://example.com/transactions/league/other/2019/4", allowed)
    with pytest.raises(ValueError):
        m._validate_final(requested, "https://amp.nfl.com/transactions/league/other/2019/5", allowed)


def test_forward_cursor_extraction_is_same_path_only_and_unique():
    html = """
    <a href="/transactions/league/waivers/2020/10?after=a%3D">A</a>
    <a href="https://www.nfl.com/transactions/league/waivers/2020/10?after=a%3D">A duplicate</a>
    <a href="/transactions/league/waivers/2020/11?after=b">wrong month</a>
    """
    assert m._forward_after_values(
        html,
        "https://amp.nfl.com/transactions/league/waivers/2020/10",
        "/transactions/league/waivers/2020/10",
    ) == ["a="]
