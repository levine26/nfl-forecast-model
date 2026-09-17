from __future__ import annotations

from research import levline4_2026_ngs_player_id_browser_heldout_v8 as v8
from research import levline4_2026_ngs_player_id_browser_heldout_v7 as v7


def test_frozen_query_grammar():
    for value in ("Kenneth Murray Jr.", "D'Andre Swift", "Amon-Ra St. Brown", "Trebor Pena"):
        assert v8.grammar_valid(value)
    for value in ("Kenneth Murray, Jr.", "Trebor Peña", 'Francis "Sisi" Mauigoa'):
        assert not v8.grammar_valid(value)


def test_addendum_forces_source_canonical_representation_when_semantic_keys_equal():
    target = {
        "visible_name": "Trebor Peña",
        "canonical_data_name": "pena,trebor",
    }
    assert v7.base.name_key(target["visible_name"]) == v7.base.name_key("Trebor Pena")
    plan = v8.query_plan(target)
    assert plan[0] == ("exact_visible_name", "Trebor Peña")
    assert ("source_canonical_name", "trebor pena") in plan
    assert plan.index(("source_canonical_name", "trebor pena")) > 0


def test_addendum_does_not_rewrite_invalid_visible_query():
    target = {
        "visible_name": 'Francis "Sisi" Mauigoa',
        "canonical_data_name": "mauigoa,francis",
    }
    plan = v8.query_plan(target)
    assert plan[0] == ("exact_visible_name", 'Francis "Sisi" Mauigoa')
    assert not v8.grammar_valid(plan[0][1])
    assert ("source_canonical_name", "francis mauigoa") in plan
    assert v8.grammar_valid("francis mauigoa")


def test_v7_frozen_resolution_semantics_are_reused_for_canonical_candidate():
    target = {
        "visible_name": "Hollywood Brown",
        "canonical_data_name": "brown,marquise",
        "team": "PHI",
        "position": "WR",
        "jersey_number": "5",
    }
    payload = {
        "players": [
            {
                "displayName": "Marquise Brown",
                "teamAbbr": "PHI",
                "position": "WR",
                "positionGroup": "WR",
                "uniformNumber": 5,
                "gsisId": "00-0031234",
            }
        ]
    }
    result = v7.resolve_target(target, payload)
    assert result["resolved"] is True
    assert result["selected_gsis_id"] == "00-0031234"
    assert result["selected_name_representation"] == "source_canonical"


def test_grammar_stress_gates_require_skip_execute_and_resolution(monkeypatch):
    baseline_metrics = {
        "team_alias_ari_selected_ngs_az_count": 1,
        "source_canonical_query_success_count": 1,
        "fallback_success_count": 1,
        "tiebreak_success_count": 1,
    }
    monkeypatch.setattr(
        v8.v7,
        "evaluate_gates",
        lambda *args, **kwargs: (dict(baseline_metrics), {"baseline": True}, True, {}),
    )
    targets = []
    results = []
    for index in range(6):
        row = {
            "team": f"T{index}",
            "visible_name": f"Name{index}",
            "profile_path": f"/p/{index}",
            "_strata": ["query_grammar_stress"],
        }
        targets.append(row)
        results.append(
            {
                "target_row_identity": [row["team"], row["visible_name"], row["profile_path"]],
                "planned_query_representations": [
                    {
                        "query_kind": "exact_visible_name",
                        "query": row["visible_name"],
                        "grammar_valid": False,
                        "disposition": "skipped_pre_dispatch_query_grammar",
                    },
                    {
                        "query_kind": "source_canonical_name",
                        "query": f"Canonical {index}",
                        "grammar_valid": True,
                        "disposition": "executed",
                    },
                ],
                "query_attempts": [
                    {
                        "query_kind": "source_canonical_name",
                        "http_status": 200,
                        "parseable_players_array": True,
                    }
                ],
                "resolved": True,
            }
        )
    contract = {
        "frozen_pass_gates": {
            "query_grammar_stress_visible_skip_required_count": 6,
            "query_grammar_stress_source_canonical_execution_required_count": 6,
            "query_grammar_stress_unique_resolution_required_count": 6,
            "query_grammar_stress_unique_resolution_required_fraction": 1.0,
        }
    }
    metrics, gates, passed, conditional = v8.evaluate_gates(
        targets, results, contract, True, 1
    )
    assert passed is True
    assert metrics["query_grammar_stress_visible_skip_count"] == 6
    assert metrics["query_grammar_stress_source_canonical_execution_count"] == 6
    assert metrics["query_grammar_stress_unique_resolution_count"] == 6
    assert all(gates.values())
    assert conditional["query_grammar_guard_qualified"] is True
