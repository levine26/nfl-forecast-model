from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.player_impact_engine import (
    ENGINE_VERSION,
    build_expected_lineup_impacts,
    build_game_matchup_context,
    validate_expected_lineup_inputs,
)


def _lineup() -> pd.DataFrame:
    rows = []
    specs = [
        ("HOME", "h-qb", "Home QB", "qb", "starter", 1.0, 0.50, 0.00, 0.90, 0.10, 0.05, "qualified"),
        ("HOME", "h-wr", "Home WR", "skill", "wr1", 0.35, 0.30, 0.05, 0.50, 0.15, 0.20, "prospective_unqualified"),
        ("HOME", "h-ol", "Home LT", "ol", "lt", 0.20, 0.25, 0.10, 0.75, 0.10, 0.10, "qualified"),
        ("HOME", "h-edge", "Home Edge", "pass_rush", "edge1", 0.25, 0.22, 0.05, 0.80, 0.12, 0.10, "qualified"),
        ("HOME", "h-dl", "Home DL", "run_defense", "dl1", 0.25, 0.18, 0.05, 0.85, 0.11, 0.08, "qualified"),
        ("HOME", "h-cb", "Home CB", "secondary", "cb1", 0.25, 0.20, 0.05, 0.70, 0.12, 0.15, "unknown"),
        ("AWAY", "a-qb", "Away QB", "qb", "starter", 1.0, 0.35, 0.00, 1.00, 0.10, 0.00, "qualified"),
        ("AWAY", "a-wr", "Away WR", "skill", "wr1", 0.35, 0.24, 0.05, 1.00, 0.12, 0.00, "qualified"),
        ("AWAY", "a-ol", "Away LT", "ol", "lt", 0.20, 0.15, 0.10, 1.00, 0.10, 0.00, "qualified"),
        ("AWAY", "a-edge", "Away Edge", "pass_rush", "edge1", 0.25, 0.30, 0.05, 1.00, 0.10, 0.00, "qualified"),
        ("AWAY", "a-dl", "Away DL", "run_defense", "dl1", 0.25, 0.20, 0.05, 1.00, 0.10, 0.00, "qualified"),
        ("AWAY", "a-cb", "Away CB", "secondary", "cb1", 0.25, 0.28, 0.05, 1.00, 0.10, 0.00, "qualified"),
    ]
    for team, pid, name, unit, role, share, value, replacement, p_active, v_unc, a_unc, source in specs:
        rows.append({
            "game_id": "2026_01_AWAY_HOME",
            "season": 2026,
            "week": 1,
            "team": team,
            "player_id": pid,
            "player_name": name,
            "unit": unit,
            "role": role,
            "modeled_player_value": value,
            "replacement_value": replacement,
            "expected_role_share": share,
            "availability_probability": p_active,
            "value_uncertainty": v_unc,
            "availability_uncertainty": a_unc,
            "feature_data_horizon": "known before authoritative T-120 boundary",
            "availability_source_status": source,
        })
    return pd.DataFrame(rows)


def test_expected_lineup_engine_aggregates_loss_gain_units_and_uncertainty_without_probability_authorization():
    result = build_expected_lineup_impacts(_lineup())
    players = result.player_impacts
    teams = result.team_impacts

    assert result.audit["engine_version"] == ENGINE_VERSION
    assert result.audit["retrospective_snap_imputation_used"] == 0
    assert result.audit["outcomes_used"] == 0
    assert players.research_only.all()
    assert not players.probability_feature_authorized.any()
    assert not teams.probability_feature_authorized.any()

    home_qb = players[players.player_id.eq("h-qb")].iloc[0]
    expected_loss = (1.0 - 0.90) * 1.0 * (0.50 - 0.00)
    assert np.isclose(home_qb.expected_lineup_value_lost, expected_loss)
    assert np.isclose(home_qb.expected_value_over_replacement, 0.90 * 0.50)
    assert home_qb.impact_uncertainty > 0

    home = teams[teams.team.eq("HOME")].iloc[0]
    assert np.isclose(home.qb_impact, home_qb.expected_value_over_replacement)
    assert home.expected_lineup_value_lost > 0
    assert home.lineup_impact_uncertainty > 0
    assert home.unqualified_or_unknown_availability_rows == 2


def test_matchup_context_produces_signed_unit_risk_without_win_probability():
    result = build_expected_lineup_impacts(_lineup())
    schedules = pd.DataFrame([{
        "game_id": "2026_01_AWAY_HOME",
        "home_team": "HOME",
        "away_team": "AWAY",
    }])
    context = build_game_matchup_context(schedules, result.team_impacts)
    row = context.iloc[0]
    assert np.isfinite(row.home_pass_protection_risk)
    assert np.isfinite(row.home_receiving_matchup_risk)
    assert np.isfinite(row.home_run_matchup_risk)
    assert row.research_only
    assert not row.probability_feature_authorized
    assert "final_home_prob" not in context.columns


def test_availability_is_explicit_and_retrospective_snap_or_outcome_fields_fail_closed():
    frame = _lineup()
    frame["actual_snap_share"] = 0.9
    with pytest.raises(ValueError, match="retrospective/current-game"):
        validate_expected_lineup_inputs(frame)

    frame = _lineup()
    frame["actual_home_score"] = 24
    with pytest.raises(ValueError, match="retrospective/current-game"):
        validate_expected_lineup_inputs(frame)


def test_missing_identity_invalid_unit_and_invalid_availability_fail_closed():
    frame = _lineup()
    frame.loc[0, "player_id"] = ""
    with pytest.raises(ValueError, match="Stable player_id"):
        validate_expected_lineup_inputs(frame)

    frame = _lineup()
    frame.loc[0, "unit"] = "punter_magic"
    with pytest.raises(ValueError, match="Unregistered"):
        validate_expected_lineup_inputs(frame)

    frame = _lineup()
    frame.loc[0, "availability_probability"] = 1.2
    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        validate_expected_lineup_inputs(frame)


def test_engine_never_infers_missing_availability_or_replacement_values():
    frame = _lineup()
    frame.loc[0, "availability_probability"] = np.nan
    with pytest.raises(ValueError, match="numeric field is incomplete"):
        validate_expected_lineup_inputs(frame)

    frame = _lineup()
    frame.loc[0, "replacement_value"] = np.nan
    with pytest.raises(ValueError, match="numeric field is incomplete"):
        validate_expected_lineup_inputs(frame)
