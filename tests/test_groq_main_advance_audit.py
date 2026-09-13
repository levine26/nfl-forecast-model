from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_groq_main_advance.py"
spec = importlib.util.spec_from_file_location("audit_groq_main_advance", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
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
    assert audit.research_only == ()
    assert audit.non_output == ()


def test_isolated_research_namespaces_are_reconcilable() -> None:
    paths = [
        ".github/workflows/research_v09b_modern_gamebook_structure_probe_v1.yml",
        "docs/levline4/modern-gamebook-structure.md",
        "research/availability/v09b_modern_gamebook_structure_probe_contract_v1.json",
        "research/availability/v09b_modern_gamebook_structure_probe_v1_receipt.json",
        "research/test_v09b_modern_gamebook_structure_probe_v1.py",
        "research/v09b_modern_gamebook_structure_probe_v1.py",
        "scripts/run_research_v09b_modern_gamebook_structure_probe_v1.py",
        "tests/test_research_v09b_modern_gamebook_structure_probe_v1.py",
        "outputs/market_t120_research.csv",
        "outputs/this_week.csv",
    ]
    audit = module.audit_main_advance(paths)
    assert audit.safe_to_reconcile
    assert audit.research_sensitive == ()
    assert audit.non_output == ()
    assert audit.research_only == tuple(sorted(paths[:8]))


def test_research_prefix_does_not_whitelist_production_paths() -> None:
    audit = module.audit_main_advance(
        [
            ".github/workflows/groq_media_writer.yml",
            "scripts/audit_groq_main_advance.py",
            "tests/test_groq_main_advance_audit.py",
            "src/nfl_forecast/media_context.py",
        ]
    )
    assert not audit.safe_to_reconcile
    assert audit.research_only == ()
    assert audit.non_output == (
        ".github/workflows/groq_media_writer.yml",
        "scripts/audit_groq_main_advance.py",
        "src/nfl_forecast/media_context.py",
        "tests/test_groq_main_advance_audit.py",
    )


def test_mixed_research_and_material_change_still_fails_closed() -> None:
    audit = module.audit_main_advance(
        [
            "research/availability/safe_receipt.json",
            ".github/workflows/research_safe_probe.yml",
            "src/nfl_forecast/source_policy.py",
        ]
    )
    assert not audit.safe_to_reconcile
    assert audit.research_only == (
        ".github/workflows/research_safe_probe.yml",
        "research/availability/safe_receipt.json",
    )
    assert audit.non_output == ("src/nfl_forecast/source_policy.py",)


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


def test_current_run_fallback_status_is_saved_outside_worktree(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    sidecar = tmp_path / "fallback-sidecar.json"
    status_path.write_text(json.dumps({
        "generated_utc": "2026-09-13T00:30:00Z",
        "groq_provider_fallback": {
            "run_id": "101",
            "status": "degraded",
            "games": {
                "2026_01_CLE_JAX": {
                    "provider_result": "failed",
                    "fallback_source": "last_validated_editorial",
                    "requires_chatgpt_refresh": True,
                }
            },
        },
    }))

    assert module.persist_current_run_fallback_status(
        status_path=status_path,
        sidecar_path=sidecar,
        run_id="101",
    )
    preserved = json.loads(sidecar.read_text())
    assert preserved["run_id"] == "101"
    assert preserved["games"]["2026_01_CLE_JAX"]["requires_chatgpt_refresh"] is True


def test_fallback_status_from_another_run_is_not_preserved(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    sidecar = tmp_path / "fallback-sidecar.json"
    status_path.write_text(json.dumps({
        "groq_provider_fallback": {
            "run_id": "old-run",
            "games": {"g": {"requires_chatgpt_refresh": True}},
        }
    }))

    assert not module.persist_current_run_fallback_status(
        status_path=status_path,
        sidecar_path=sidecar,
        run_id="new-run",
    )
    assert not sidecar.exists()
