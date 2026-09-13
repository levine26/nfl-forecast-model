from __future__ import annotations

from research.v09b_legacy_gamebook_identity_audit_v2 import (
    EXPECTED_POPULATION,
    EXPECTED_V1_EXACT_RESOLVED,
    SEASONS,
    aggregate_receipts,
    resolve_candidates,
)


def test_exact_unique_match_has_precedence_over_same_jersey_candidates() -> None:
    method, gsis = resolve_candidates({"00-0000001"}, {"00-0000001", "00-0000002"})
    assert method == "exact_v1"
    assert gsis == "00-0000001"


def test_exact_ambiguity_may_not_fall_back_to_unique_jersey_candidate() -> None:
    method, gsis = resolve_candidates(
        {"00-0000001", "00-0000002"},
        {"00-0000001"},
    )
    assert method == "ambiguous_exact_v1"
    assert gsis is None


def test_exact_zero_may_resolve_only_one_same_week_team_jersey_candidate() -> None:
    method, gsis = resolve_candidates(set(), {"00-0000001"})
    assert method == "unique_same_week_team_jersey"
    assert gsis == "00-0000001"


def test_zero_same_jersey_candidate_remains_unresolved() -> None:
    method, gsis = resolve_candidates(set(), set())
    assert method == "unresolved_zero_same_week_team_jersey"
    assert gsis is None


def test_multiple_same_jersey_candidates_remain_ambiguous() -> None:
    method, gsis = resolve_candidates(set(), {"00-0000001", "00-0000002"})
    assert method == "ambiguous_multiple_same_week_team_jersey"
    assert gsis is None


def _receipt(
    season: int,
    *,
    fallback: int,
    unresolved_zero: int = 0,
    ambiguous_fallback: int = 0,
    source_integrity: bool = True,
) -> dict[str, object]:
    exact = EXPECTED_V1_EXACT_RESOLVED[season]
    total = EXPECTED_POPULATION[season]
    unresolved = total - exact - fallback - unresolved_zero - ambiguous_fallback
    assert unresolved == 0
    resolved = exact + fallback
    return {
        "season": season,
        "source_integrity_gates_pass": source_integrity,
        "weekly_roster_status_used": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "gamebook_identities_total": total,
        "exact_v1_resolved": exact,
        "unique_same_week_team_jersey_resolved": fallback,
        "ambiguous_exact_v1": 0,
        "ambiguous_multiple_same_week_team_jersey": ambiguous_fallback,
        "unresolved_zero_same_week_team_jersey": unresolved_zero,
        "resolved_total": resolved,
        "unresolved_or_ambiguous_total": unresolved_zero + ambiguous_fallback,
        "season_resolution_rate": resolved / total,
    }


def _observed_shape_receipts() -> list[dict[str, object]]:
    return [
        _receipt(2012, fallback=313),
        _receipt(2013, fallback=298),
        _receipt(2014, fallback=264),
        _receipt(2015, fallback=252),
        _receipt(2016, fallback=321, unresolved_zero=377, ambiguous_fallback=7),
    ]


def test_aggregate_gate_qualifies_observed_shape_without_per_season_threshold() -> None:
    result = aggregate_receipts(_observed_shape_receipts())
    assert result["legacy_identity_population"] == 135572
    assert result["exact_v1_resolved"] == 133740
    assert result["unique_same_week_team_jersey_resolved"] == 1448
    assert result["resolved_total"] == 135188
    assert result["unresolved_zero_same_week_team_jersey"] == 377
    assert result["ambiguous_multiple_same_week_team_jersey"] == 7
    assert result["unresolved_or_ambiguous_total"] == 384
    assert result["aggregate_identity_resolution_rate"] == 135188 / 135572
    assert result["aggregate_identity_resolution_gate_pass"] is True
    assert result["legacy_player_team_game_identity_qualified"] is True
    assert result["season_receipts"]["2016"]["season_resolution_rate"] < 0.995
    assert result["unresolved_identities_silently_dropped"] is False
    assert result["v09b_model_fit_authorized"] is False


def test_aggregate_fails_if_any_season_source_integrity_fails() -> None:
    receipts = _observed_shape_receipts()
    receipts[0]["source_integrity_gates_pass"] = False
    result = aggregate_receipts(receipts)
    assert result["source_integrity_all_seasons_pass"] is False
    assert result["legacy_player_team_game_identity_qualified"] is False


def test_aggregate_requires_exactly_one_receipt_per_frozen_season() -> None:
    receipts = _observed_shape_receipts()
    try:
        aggregate_receipts(receipts[:-1])
    except RuntimeError as exc:
        assert "exactly seasons" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing season did not fail closed")


def test_aggregate_denominator_drift_fails_qualification() -> None:
    receipts = _observed_shape_receipts()
    receipts[0] = dict(receipts[0])
    receipts[0]["gamebook_identities_total"] = int(receipts[0]["gamebook_identities_total"]) + 1
    receipts[0]["unresolved_zero_same_week_team_jersey"] = 1
    receipts[0]["unresolved_or_ambiguous_total"] = 1
    result = aggregate_receipts(receipts)
    assert result["legacy_identity_population_matches_frozen_denominator"] is False
    assert result["legacy_player_team_game_identity_qualified"] is False


def test_all_five_frozen_seasons_are_present() -> None:
    assert SEASONS == (2012, 2013, 2014, 2015, 2016)
