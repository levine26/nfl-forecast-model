from __future__ import annotations

import json
from pathlib import Path

from research import v09b_nfl_transaction_empty_semantics_v7 as m

CONTRACT = Path("research/availability/v09b_nfl_transaction_empty_semantics_v7_contract.json")
V6_CONTRACT = Path("research/availability/v09b_nfl_transaction_no_header_source_shape_v6_contract.json")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_candidate_rule_is_exact_and_fail_closed():
    c = _contract()
    record = {
        "headings": ["2019 NFL Transactions", "No Transactions Available"],
        "standard_transaction_header_seen": False,
        "standard_transaction_row_count": 0,
        "table_count": 0,
        "distinct_forward_after_cursor_count": 0,
    }
    assert m._candidate_rule(record, c) is True
    for field, bad in [
        ("headings", ["No transactions available"]),
        ("standard_transaction_header_seen", True),
        ("standard_transaction_row_count", 1),
        ("table_count", 1),
        ("distinct_forward_after_cursor_count", 1),
    ]:
        changed = dict(record)
        changed[field] = bad
        assert m._candidate_rule(changed, c) is False


def test_current_cursor_echo_is_not_a_distinct_forward_cursor():
    requested = "https://amp.nfl.com/transactions/league/waivers/2017/5?after=current%3D"
    assert m._distinct_forward_values(["current=", "next="], requested) == ["next="]
    assert m._distinct_forward_values(["current="], requested) == []


def test_positive_universe_is_hash_locked_72_cases():
    c = _contract()
    v6 = json.loads(V6_CONTRACT.read_text(encoding="utf-8"))
    assert c["positive_cases"]["expected_count"] == 72
    assert len(v6["scope"]["fixed_requests"]) == 72
    assert sum(x["kind"] == "initial" for x in v6["scope"]["fixed_requests"]) == 70
    assert sum(x["kind"] == "post_pagination" for x in v6["scope"]["fixed_requests"]) == 2


def test_negative_control_universe_is_30_plus_2():
    c = _contract()
    grid = c["negative_controls"]["september_grid"]
    assert len(grid["years"]) * len(grid["categories"]) == 30
    assert grid["month"] == 9
    assert len(c["negative_controls"]["pre_terminal_cursor_pages"]) == 2
    assert c["negative_controls"]["expected_total_count"] == 32


def test_preterminal_controls_are_exactly_linked_to_v6_positive_cursors():
    c = _contract()
    v6 = json.loads(V6_CONTRACT.read_text(encoding="utf-8"))
    positive_urls = {x["requested_url"] for x in v6["scope"]["fixed_requests"]}
    for control in c["negative_controls"]["pre_terminal_cursor_pages"]:
        target = control["expected_distinct_forward_after_cursor"]
        base = control["requested_url"].split("?", 1)[0]
        from urllib.parse import quote
        assert f"{base}?after={quote(target, safe='')}" in positive_urls
        assert control["standard_transaction_rows_expected"] == 25


def test_pass_authority_remains_narrow():
    c = _contract()
    a = c["authority_if_gate_passes"]
    assert a["explicit_no_transactions_empty_result_semantics_qualified"] is True
    assert a["post_pagination_explicit_empty_terminal_semantics_qualified"] is True
    assert a["all_month_full_ledger_qualified"] is False
    assert a["transaction_state_machine_defined"] is False
    assert a["modern_game_day_roster_universe_qualified"] is False
    assert a["training_label_semantics_qualified"] is False
    assert a["training_source_chronology_qualified"] is False
    assert a["v09b_model_fit_authorized"] is False
    assert c["governance"]["completed_2026_outcomes_used"] == 0
