from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_groq_main_advance.py"
spec = importlib.util.spec_from_file_location("audit_groq_main_advance", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": "g1",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-13",
                "gametime": "13:00",
                "away_team": "BUF",
                "home_team": "HOU",
                "pick": "BUF",
                "final_probability_strategy": "F-ST-01-FROZEN-2026",
                "fst_artifact_id": "F-ST-01-FROZEN-2026",
                "final_home_prob": 0.46,
                "spread_line": -1.5,
            },
            {
                "game_id": "g2",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-13",
                "gametime": "16:25",
                "away_team": "ARI",
                "home_team": "LAC",
                "pick": "LAC",
                "final_probability_strategy": "F-ST-01-FROZEN-2026",
                "fst_artifact_id": "F-ST-01-FROZEN-2026",
                "final_home_prob": 0.81,
                "spread_line": 9.5,
            },
        ]
    )


def test_daily_forecast_and_diagnostic_outputs_are_reconcilable() -> None:
    audit = module.audit_main_advance(
        [
            "outputs/this_week.csv",
            "outputs/run_history.csv",
            "outputs/status.json",
            "outputs/calibration.csv",
            "outputs/confidence_diagnostics.csv",
            "outputs/history_scoreboard.json",
            "outputs/model_leaderboard.csv",
            "outputs/movement_attribution.csv",
            "outputs/power_editorial.json",
            "outputs/power_ratings.csv",
            "outputs/prediction_history.csv",
            "outputs/team_profiles.csv",
            "outputs/weekly_brief.json",
        ]
    )
    assert audit.safe_to_reconcile
    assert audit.research_sensitive == ()
    assert audit.non_output == ()


def test_context_and_provider_outputs_force_fresh_research() -> None:
    for path in sorted(module.RESEARCH_SENSITIVE_OUTPUTS):
        audit = module.audit_main_advance(["outputs/this_week.csv", path])
        assert not audit.safe_to_reconcile
        assert audit.research_sensitive == (path,)


def test_code_or_workflow_change_forces_fresh_research() -> None:
    audit = module.audit_main_advance(
        [
            "outputs/this_week.csv",
            "src/nfl_forecast/media_context.py",
            ".github/workflows/context.yml",
        ]
    )
    assert not audit.safe_to_reconcile
    assert audit.non_output == (
        ".github/workflows/context.yml",
        "src/nfl_forecast/media_context.py",
    )


def test_duplicate_and_blank_paths_are_normalized() -> None:
    audit = module.audit_main_advance(["", "outputs/status.json", " outputs/status.json "])
    assert audit.changed == ("outputs/status.json",)
    assert audit.safe_to_reconcile


def test_probability_line_and_score_movement_do_not_invalidate_research_contract() -> None:
    before = _frame()
    after = _frame()
    after.loc[after["game_id"] == "g1", "final_home_prob"] = 0.49
    after.loc[after["game_id"] == "g1", "spread_line"] = -2.5
    assert module.forecast_contract_differences(before, after) == []


def test_pick_flip_invalidates_research_contract() -> None:
    before = _frame()
    after = _frame()
    after.loc[after["game_id"] == "g1", "pick"] = "HOU"
    assert module.forecast_contract_differences(before, after) == [
        "g1: pick changed 'BUF' -> 'HOU'"
    ]


def test_kickoff_or_model_identity_change_invalidates_research_contract() -> None:
    before = _frame()
    after = _frame()
    after.loc[after["game_id"] == "g2", "gametime"] = "20:20"
    after.loc[after["game_id"] == "g2", "fst_artifact_id"] = "F-ST-02"
    differences = module.forecast_contract_differences(before, after)
    assert "g2: gametime changed '16:25' -> '20:20'" in differences
    assert "g2: fst_artifact_id changed 'F-ST-01-FROZEN-2026' -> 'F-ST-02'" in differences


def test_slate_membership_change_invalidates_research_contract() -> None:
    before = _frame()
    after = _frame().iloc[[0]].copy()
    assert module.forecast_contract_differences(before, after) == [
        "g2: removed from canonical slate"
    ]


def test_duplicate_game_id_in_contract_fails_closed() -> None:
    duplicated = pd.concat([_frame(), _frame().iloc[[0]]], ignore_index=True)
    try:
        module.forecast_contract_differences(duplicated, _frame())
    except ValueError as exc:
        assert "duplicate game_id" in str(exc)
    else:
        raise AssertionError("duplicate game_id must fail closed")


def test_missing_contract_field_fails_closed() -> None:
    broken = _frame().drop(columns=["pick"])
    try:
        module.forecast_contract_differences(broken, _frame())
    except ValueError as exc:
        assert "missing research-contract fields" in str(exc)
        assert "pick" in str(exc)
    else:
        raise AssertionError("missing research-contract field must fail closed")
