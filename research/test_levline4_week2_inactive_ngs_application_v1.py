from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

from research import levline4_week2_inactive_ngs_application_v1 as app


def _write_gz(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as handle:
        handle.write(raw)


def _source(raw: bytes, relpath: str, url: str = "https://www.nfl.com/news/inactive-test") -> dict:
    return {
        "source_kind": "nfl_inactives_news_article",
        "url": url,
        "http_status": 200,
        "raw_body_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_object_relpath": relpath,
    }


def _html(*teams: str) -> bytes:
    names = {"ARI": "CARDINALS", "LAC": "CHARGERS", "NYG": "GIANTS", "DAL": "COWBOYS"}
    parts = ["<html><body>"]
    for index, team in enumerate(teams):
        parts.append(f"<h3>{names[team]}</h3><ul><li>WR Synthetic Player {index}</li></ul>")
    parts.append("</body></html>")
    return "".join(parts).encode()


def _contract() -> dict:
    return json.loads(
        Path("research/levline4_week2_inactive_ngs_application_v1_contract.json").read_text()
    )


def test_frozen_contract_and_addendum_governance():
    contract = _contract()
    assert contract["contract_id"] == app.CONTRACT_ID
    assert contract["status"] == "PREREGISTERED_BEFORE_FIRST_WEEK2_REAL_TARGET_EXPOSURE"
    assert contract["empirical_boundary"]["week2_inactive_target_identities_observed_before_contract_freeze"] == 0
    assert contract["empirical_boundary"]["week2_inactive_ngs_target_requests_observed_before_contract_freeze"] == 0
    assert contract["frozen_per_cohort_pass_gates"]["unique_resolution_minimum_fraction"] == 0.953125
    assert contract["frozen_ngs_query_and_resolution"]["position_or_jersey_tiebreak_allowed"] is False
    assert contract["authority_if_per_cohort_passes"]["availability_probability_feature_authorized"] is False
    assert contract["authority_if_per_cohort_passes"]["forecast_probability_effect_authorized"] is False
    assert contract["authority_if_per_cohort_passes"]["production_authorized"] is False

    addendum = json.loads(
        Path("research/levline4_week2_inactive_ngs_application_v1_preexecution_addendum.json").read_text()
    )
    assert addendum["frozen_parent_contract_commit"] == "bcd246bfb3957ef2076d3042c0b2aa11a943b55a"
    assert addendum["empirical_boundary"]["week2_inactive_player_targets_observed_before_addendum"] == 0
    assert addendum["empirical_boundary"]["application_workflow_runs_before_addendum"] == 0
    assert addendum["frozen_clarification"]["all_other_contract_rules"] == "UNCHANGED"


def test_cohort_key_is_order_invariant_and_week2_bound():
    games_a = [{"game_id": "2026_02_ARI_LAC"}, {"game_id": "2026_02_NYG_DAL"}]
    games_b = list(reversed(games_a))
    assert app.cohort_key(games_a) == app.cohort_key(games_b)
    assert len(app.cohort_key(games_a)) == 64


def test_structural_team_selection_is_heading_only(tmp_path: Path):
    raw = _html("ARI", "LAC")
    assert app.structural_team_set(raw) == {"ARI", "LAC"}
    relpath = "raw/body.html.gz"
    _write_gz(tmp_path / relpath, raw)
    observation = {
        "due_games": [
            {"game_id": "2026_02_ARI_LAC", "away_team": "ARI", "home_team": "LAC"}
        ],
        "sources": [_source(raw, relpath)],
    }
    selected, matches = app.select_structural_article(tmp_path, observation)
    assert selected is not None
    assert selected["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert selected["structural_teams"] == ["ARI", "LAC"]
    assert len(matches) == 1


def test_structural_selection_waits_without_matching_due_teams(tmp_path: Path):
    raw = _html("NYG", "DAL")
    relpath = "raw/body.html.gz"
    _write_gz(tmp_path / relpath, raw)
    observation = {
        "due_games": [
            {"game_id": "2026_02_ARI_LAC", "away_team": "ARI", "home_team": "LAC"}
        ],
        "sources": [_source(raw, relpath)],
    }
    selected, matches = app.select_structural_article(tmp_path, observation)
    assert selected is None
    assert matches == []


def test_structural_selection_fails_closed_on_two_distinct_matching_bodies(tmp_path: Path):
    raw1 = _html("ARI", "LAC")
    raw2 = raw1.replace(b"Synthetic Player 0", b"Different Synthetic 0")
    for index, raw in enumerate((raw1, raw2), 1):
        _write_gz(tmp_path / f"raw/{index}.html.gz", raw)
    observation = {
        "due_games": [
            {"game_id": "2026_02_ARI_LAC", "away_team": "ARI", "home_team": "LAC"}
        ],
        "sources": [
            _source(raw1, "raw/1.html.gz", "https://www.nfl.com/news/inactive-a"),
            _source(raw2, "raw/2.html.gz", "https://www.nfl.com/news/inactive-b"),
        ],
    }
    with pytest.raises(RuntimeError, match="multiple distinct structurally matching"):
        app.select_structural_article(tmp_path, observation)


def test_roster_canonical_enrichment_requires_unique_same_team_row():
    roster = [
        {
            "team": "MIA",
            "visible_name": "Josh Uche",
            "canonical_data_name": "Uche,Joshua",
            "position": "LB",
            "jersey_number": "55",
            "profile_path": "/ignored",
        },
        {
            "team": "NE",
            "visible_name": "Josh Uche",
            "canonical_data_name": "Uche,Joshua",
            "position": "LB",
            "jersey_number": "55",
            "profile_path": "/ignored-2",
        },
    ]
    enriched = app.canonical_roster_enrichment("MIA", "Josh Uche", roster)
    assert enriched["unique_enrichment"] is True
    assert enriched["canonical_query_name"] == "Joshua Uche"
    assert enriched["position_used"] is False
    assert enriched["jersey_used"] is False
    assert enriched["profile_path_used"] is False
    assert enriched["roster_match_resolves_gsis"] is False


def test_roster_canonical_enrichment_fails_closed_on_multiple_same_team_rows():
    roster = [
        {"team": "MIA", "visible_name": "Josh Uche", "canonical_data_name": "Uche,Joshua"},
        {"team": "MIA", "visible_name": "Josh Uche", "canonical_data_name": "Uche,Joshua"},
    ]
    enriched = app.canonical_roster_enrichment("MIA", "Josh Uche", roster)
    assert enriched["matching_roster_row_count"] == 2
    assert enriched["unique_enrichment"] is False
    assert enriched["canonical_query_name"] is None


def test_v8_query_plan_skips_invalid_surface_but_includes_source_canonical():
    enrichment = {
        "unique_enrichment": True,
        "canonical_data_name": "Swift,D'Andre",
        "canonical_query_name": "D'Andre Swift",
    }
    plan = app.application_query_plan("D’Andre Swift", enrichment)
    assert plan[0] == ("exact_visible_name", "D’Andre Swift")
    assert ("source_canonical_name", "D'Andre Swift") in plan
    assert app.v8.grammar_valid("D’Andre Swift") is False
    assert app.v8.grammar_valid("D'Andre Swift") is True


def _candidate(name: str, team: str, gsis: str, position: str = "WR", jersey: int = 1) -> dict:
    return {
        "displayName": name,
        "teamAbbr": team,
        "gsisId": gsis,
        "position": position,
        "positionGroup": position,
        "uniformNumber": jersey,
    }


def test_resolution_exact_single_candidate_and_ari_az_alias():
    enrichment = {"unique_enrichment": False, "canonical_query_name": None}
    resolved = app.resolve_payload(
        team="ARI",
        rendered_name="Synthetic Player",
        enrichment=enrichment,
        payload={"players": [_candidate("Synthetic Player", "AZ", "00-1234567")]},
    )
    assert resolved["resolved"] is True
    assert resolved["selected_gsis_id"] == "00-1234567"
    assert resolved["ambiguous"] is False
    assert resolved["tiebreak_applied"] is False


def test_multiple_primary_candidates_are_ambiguous_without_tiebreak():
    enrichment = {"unique_enrichment": False, "canonical_query_name": None}
    payload = {
        "players": [
            _candidate("Synthetic Player", "MIA", "00-1234567", "WR", 1),
            _candidate("Synthetic Player", "MIA", "00-7654321", "LB", 55),
        ]
    }
    resolved = app.resolve_payload(
        team="MIA",
        rendered_name="Synthetic Player",
        enrichment=enrichment,
        payload=payload,
    )
    assert resolved["resolved"] is False
    assert resolved["ambiguous"] is True
    assert resolved["primary_candidate_count"] == 2
    assert resolved["tiebreak_applied"] is False


def test_global_audit_is_never_fallback():
    results = [
        {
            "target_id": "t1",
            "team": "MIA",
            "player_name_rendered": "Synthetic Player",
            "selected_gsis_id": "00-1234567",
            "selected_candidate": {"displayName": "Synthetic Player"},
        },
        {
            "target_id": "t2",
            "team": "MIA",
            "player_name_rendered": "Other Player",
            "selected_gsis_id": None,
            "selected_candidate": None,
        },
    ]
    audits = app.audit_results(results, {"synthetic player": {"00-1234567"}})
    assert audits[0]["audit_state"] == "CROSS_SOURCE_CORROBORATED"
    assert audits[1]["audit_state"] == "APPLICATION_NOT_RESOLVED"
    assert all(row["global_source_used_as_fallback"] is False for row in audits)
    assert all(row["global_source_used_for_selection"] is False for row in audits)


def _result(target_id: str, gsis: str, *, ambiguous: bool = False) -> dict:
    return {
        "target_id": target_id,
        "resolved": not ambiguous,
        "ambiguous": ambiguous,
        "selected_candidate": {"displayName": f"Player {target_id}", "gsisId": gsis},
        "selected_candidate_gsis_valid": True,
        "selected_gsis_id": None if ambiguous else gsis,
        "query_attempts": [{"http_status": 200, "parseable_players_array": True}],
    }


def test_evaluate_pass_and_authority_ceiling():
    contract = _contract()
    targets = [{"target_id": f"t{index}"} for index in range(64)]
    results = [_result(f"t{index}", f"00-{index:07d}") for index in range(63)]
    results.append(
        {
            "target_id": "t63",
            "resolved": False,
            "ambiguous": False,
            "selected_candidate": None,
            "selected_candidate_gsis_valid": False,
            "selected_gsis_id": None,
            "query_attempts": [{"http_status": 200, "parseable_players_array": True}],
        }
    )
    audits = [
        {
            "target_id": row["target_id"],
            "audit_state": "CROSS_SOURCE_CORROBORATED" if row["resolved"] else "APPLICATION_NOT_RESOLVED",
        }
        for row in results
    ]
    metrics, gates, passed = app.evaluate(
        target_rows=targets,
        results=results,
        audits=audits,
        source_sha_verified=True,
        all_due_teams_present=True,
        page_loaded=True,
        query_input_count=1,
        contract=contract,
    )
    assert metrics["resolved_count"] == 63
    assert metrics["resolved_fraction"] == pytest.approx(63 / 64)
    assert all(gates.values())
    assert passed is True
    authority = app.frozen_authority(contract, passed)
    assert authority["official_inactive_identity_to_gsis_qualified_for_this_due_cohort"] is True
    assert authority["official_inactive_state_to_gsis_join_qualified_for_resolved_rows_this_due_cohort"] is True
    assert authority["availability_probability_feature_authorized"] is False
    assert authority["player_value_join_authorized"] is False
    assert authority["forecast_probability_effect_authorized"] is False
    assert authority["production_authorized"] is False


def test_evaluate_fails_ambiguity():
    contract = _contract()
    targets = [{"target_id": "a"}, {"target_id": "b"}]
    results = [_result("a", "00-1234567"), _result("b", "00-7654321", ambiguous=True)]
    audits = [
        {"target_id": "a", "audit_state": "CROSS_SOURCE_CORROBORATED"},
        {"target_id": "b", "audit_state": "APPLICATION_NOT_RESOLVED"},
    ]
    metrics, gates, passed = app.evaluate(
        target_rows=targets,
        results=results,
        audits=audits,
        source_sha_verified=True,
        all_due_teams_present=True,
        page_loaded=True,
        query_input_count=1,
        contract=contract,
    )
    assert metrics["ambiguous_target_count"] == 1
    assert gates["ambiguous_target_count_allowed"] is False
    assert gates["unique_resolution_minimum_fraction"] is False
    assert passed is False
    authority = app.frozen_authority(contract, passed)
    assert authority["official_inactive_identity_to_gsis_qualified_for_this_due_cohort"] is False
    assert authority["production_authorized"] is False
