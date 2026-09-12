from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_groq_main_advance.py"
spec = importlib.util.spec_from_file_location("audit_groq_main_advance", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


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
