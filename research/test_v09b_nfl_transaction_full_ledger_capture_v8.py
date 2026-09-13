from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from research import v09b_nfl_transaction_full_ledger_capture_v8 as m

CONTRACT = Path("research/availability/v09b_nfl_transaction_full_ledger_capture_v8_contract.json")
V6 = Path("research/availability/v09b_nfl_transaction_no_header_source_shape_v6_contract.json")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _v6() -> dict:
    return json.loads(V6.read_text(encoding="utf-8"))


def test_full_scope_is_360_endpoints():
    c = _contract()
    s = c["scope"]
    assert len(s["years"]) == 5
    assert len(s["months"]) == 12
    assert len(s["categories"]) == 6
    assert len(s["years"]) * len(s["months"]) * len(s["categories"]) == s["expected_endpoints"] == 360
    assert len(s["months"]) * len(s["categories"]) == s["expected_endpoints_per_year"] == 72


def test_expected_empty_universe_is_exactly_hash_locked_72_requests():
    v6 = _v6()
    assert len(v6["scope"]["fixed_requests"]) == 72
    expected = m._expected_empty_urls(v6)
    assert len(expected) == 72
    assert sum(len(m._expected_empty_urls(v6, year)) for year in (2017, 2018, 2019, 2020, 2021)) == 72
    assert all("/9" not in url.rsplit("/", 1)[-1] for url in [])  # no inferred shortcuts; exact set only


def test_qualified_empty_shape_is_exact_and_fail_closed():
    c = _contract()
    good = dict(
        headings=["2019 NFL Transactions", "No Transactions Available"],
        header=False,
        rows=[],
        table_count=0,
        distinct_after_values=[],
        contract=c,
    )
    assert m._qualified_empty_shape(**good) is True
    bads = [
        {"headings": ["No transactions available"]},
        {"header": True},
        {"rows": [{"name": "x"}]},
        {"table_count": 1},
        {"distinct_after_values": ["next="]},
    ]
    for patch in bads:
        case = dict(good)
        case.update(patch)
        assert m._qualified_empty_shape(**case) is False


def test_distinct_after_excludes_current_cursor_and_wrong_path():
    html = """
    <a href="/transactions/league/waivers/2020/10?after=current%3D">same</a>
    <a href="/transactions/league/waivers/2020/10?after=next%3D">next</a>
    <a href="/transactions/league/waivers/2020/11?after=wrong">wrong month</a>
    """
    requested = "https://amp.nfl.com/transactions/league/waivers/2020/10?after=current%3D"
    assert m._distinct_after_values(html, requested, requested) == ["next="]


def test_raw_capture_is_deterministic_and_exact(tmp_path):
    raw = b"source bytes\n"
    a = tmp_path / "a.html.gz"
    b = tmp_path / "b.html.gz"
    ra = m._write_raw(raw, a)
    rb = m._write_raw(raw, b)
    assert a.read_bytes() == b.read_bytes()
    assert gzip.decompress(a.read_bytes()) == raw
    assert ra["raw_sha256"] == rb["raw_sha256"] == m._sha(raw)
    assert ra["gzip_roundtrip_matches"] is True


def test_final_url_validation_is_fail_closed():
    requested = "https://amp.nfl.com/transactions/league/trades/2018/4"
    allowed = {"amp.nfl.com", "www.nfl.com"}
    m._validate_final(requested, requested, allowed)
    m._validate_final(requested, "https://www.nfl.com/transactions/league/trades/2018/4", allowed)
    with pytest.raises(ValueError):
        m._validate_final(requested, "http://amp.nfl.com/transactions/league/trades/2018/4", allowed)
    with pytest.raises(ValueError):
        m._validate_final(requested, "https://example.com/transactions/league/trades/2018/4", allowed)
    with pytest.raises(ValueError):
        m._validate_final(requested, "https://amp.nfl.com/transactions/league/trades/2018/5", allowed)


def test_success_authority_is_capture_only():
    c = _contract()
    a = c["authority_if_gate_passes"]
    assert a["all_month_full_ledger_capture_qualified"] is True
    assert a["full_ledger_source_capture_complete"] is True
    assert a["durable_full_ledger_source_archive_qualified"] is False
    assert a["transaction_state_machine_defined"] is False
    assert a["transaction_semantic_taxonomy_qualified"] is False
    assert a["same_day_transaction_order_resolved"] is False
    assert a["modern_game_day_roster_universe_qualified"] is False
    assert a["training_label_semantics_qualified"] is False
    assert a["training_source_chronology_qualified"] is False
    assert a["v09b_model_fit_authorized"] is False
    assert c["governance"]["completed_2026_outcomes_used"] == 0
