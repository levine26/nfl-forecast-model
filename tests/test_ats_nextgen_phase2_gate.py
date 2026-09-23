from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.ats_nextgen_gate import (
    HISTORICAL_MARKET_EVIDENCE_CLASS,
    assert_chronology_plan,
    build_historical_ats_gate,
    chronology_plan,
    grade_home_ats,
    validate_gate_frame,
    write_phase2_gate_artifacts,
)


def _source(rows: list[dict] | None = None) -> pd.DataFrame:
    base = {
        "game_id": "2022_01_A_B",
        "season": 2022,
        "week": 1,
        "gameday": "2022-09-11",
        "gametime": "13:00",
        "game_type": "REG",
        "away_team": "A",
        "home_team": "B",
        "home_score": 24,
        "away_score": 21,
        "spread_line": -3.0,
        "total_line": 44.5,
        "home_moneyline": -150,
        "away_moneyline": 130,
        "home_elo": 1510.0,
        "away_elo": 1490.0,
        "diff_off_epa_ewma": 0.10,
        "diff_def_epa_allowed_ewma": -0.04,
        "diff_pass_epa_ewma": 0.12,
        "diff_def_pass_epa_allowed_ewma": -0.05,
        "diff_rush_epa_ewma": 0.02,
        "diff_def_rush_epa_allowed_ewma": -0.01,
        "diff_success_rate_ewma": 0.03,
        "diff_def_success_allowed_ewma": -0.02,
        "diff_neutral_epa_ewma": 0.08,
        "rest_diff": 0.0,
    }
    if rows is None:
        return pd.DataFrame([base])
    built = []
    for i, patch in enumerate(rows):
        row = dict(base)
        row["game_id"] = f"2022_{i + 1:02d}_A_B"
        row["week"] = i + 1
        row.update(patch)
        built.append(row)
    return pd.DataFrame(built)


def test_frozen_four_synthetic_sign_examples():
    win = grade_home_ats(27, 20, -3)
    push = grade_home_ats(23, 20, -3)
    loss = grade_home_ats(22, 20, -3)
    dog_cover = grade_home_ats(20, 22, 3)

    assert (win.ats_residual, win.outcome, win.home_cover_binary) == (4.0, "HOME_COVER", 1.0)
    assert (push.ats_residual, push.outcome, push.home_cover_binary, push.push) == (
        0.0,
        "PUSH",
        None,
        True,
    )
    assert (loss.ats_residual, loss.outcome, loss.home_cover_binary) == (-1.0, "HOME_LOSS", 0.0)
    assert (dog_cover.ats_residual, dog_cover.outcome, dog_cover.home_cover_binary) == (
        1.0,
        "HOME_COVER",
        1.0,
    )


def test_whole_line_push_and_half_line_no_push_contract():
    assert grade_home_ats(24, 21, -3.0).outcome == "PUSH"
    assert grade_home_ats(24, 21, -3.5).outcome == "HOME_LOSS"
    assert grade_home_ats(24, 21, -2.5).outcome == "HOME_COVER"


def test_historical_gate_preserves_frozen_market_semantics_and_push_null_target():
    result = build_historical_ats_gate(_source())
    validate_gate_frame(result)
    row = result.iloc[0]
    assert row["market_evidence_class"] == HISTORICAL_MARKET_EVIDENCE_CLASS
    assert row["home_spread"] == -3.0
    assert row["market_home_margin_center"] == 3.0
    assert row["favorite_size"] == 3.0
    assert row["margin"] == 3.0
    assert row["ats_residual"] == 0.0
    assert row["ats_outcome"] == "PUSH"
    assert pd.isna(row["ats_home_cover"])
    assert bool(row["ats_push"]) is True
    assert row["pregame_elo_diff"] == 20.0
    assert 0.0 < row["no_vig_home_moneyline_prob"] < 1.0


def test_gate_marks_missing_mandatory_spread_ineligible_without_inventing_line():
    source = _source([{"spread_line": np.nan}])
    result = build_historical_ats_gate(source)
    row = result.iloc[0]
    assert bool(row["ats_eligible"]) is False
    assert pd.isna(row["home_spread"])
    assert pd.isna(row["ats_residual"])
    assert pd.isna(row["ats_outcome"])
    assert pd.isna(row["ats_home_cover"])


def test_gate_refuses_completed_2026_rows():
    source = _source([{"season": 2026, "game_id": "2026_01_A_B"}])
    with pytest.raises(ValueError, match="2026"):
        build_historical_ats_gate(source)


def test_gate_refuses_duplicate_game_identity():
    source = pd.concat([_source(), _source()], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate game_id"):
        build_historical_ats_gate(source)


def test_nested_chronology_is_expanding_and_never_uses_target_or_future_season():
    plan = chronology_plan(2025)
    assert plan.outer_training_seasons[0] == 2015
    assert plan.outer_training_seasons[-1] == 2024
    assert plan.inner_target_seasons == (2019, 2020, 2021, 2022, 2023, 2024)
    assert plan.inner_training_seasons[2019] == (2015, 2016, 2017, 2018)
    assert plan.inner_training_seasons[2024][-1] == 2023
    assert_chronology_plan(plan)


def test_pre_fit_manifest_records_lineage_and_is_canonically_game_keyed(tmp_path):
    source = _source([
        {"game_id": "2022_02_A_B", "week": 2, "home_score": 27, "away_score": 20},
        {"game_id": "2022_01_A_B", "week": 1, "home_score": 20, "away_score": 20, "spread_line": 1.0},
    ])
    frame = build_historical_ats_gate(source)
    manifest = write_phase2_gate_artifacts(
        frame,
        tmp_path / "first",
        source_description="synthetic historical schedule/matchup fixture",
    )
    reversed_manifest = write_phase2_gate_artifacts(
        frame.iloc[::-1].reset_index(drop=True),
        tmp_path / "second",
        source_description="synthetic historical schedule/matchup fixture",
    )

    persisted = json.loads((tmp_path / "first" / "phase2_gate_manifest.json").read_text())
    assert manifest["stage"] == "pre_result_pre_fit_gate"
    assert manifest["candidate_fitting_performed"] is False
    assert manifest["candidate_performance_generated"] is False
    assert manifest["completed_2026_outcomes_authorized"] is False
    assert manifest["random_kfold_allowed"] is False
    assert manifest["market_lineage"]["home_spread"] == "spread_line"
    assert manifest["football_feature_lineage"]["off_epa_diff"] == "diff_off_epa_ewma"
    assert persisted["artifact"]["raw_sha256"] == manifest["artifact"]["raw_sha256"]
    assert (
        manifest["artifact"]["canonical_game_keyed_sha256"]
        == reversed_manifest["artifact"]["canonical_game_keyed_sha256"]
    )
    assert manifest["artifact"]["raw_sha256"] != reversed_manifest["artifact"]["raw_sha256"]
