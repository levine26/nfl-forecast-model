from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

_FIREWALL_PATH = Path("scripts/check_research_firewall.py")
_SPEC = importlib.util.spec_from_file_location("check_research_firewall", _FIREWALL_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIREWALL = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIREWALL)
path_allowed = _FIREWALL.path_allowed
research_scope_triggered = _FIREWALL.research_scope_triggered
validate_changed_paths = _FIREWALL.validate_changed_paths


def test_research_allowlist_accepts_isolated_surfaces():
    allowed = [
        "src/nfl_forecast/challenger_evaluation.py",
        "src/nfl_forecast/challenger_v09.py",
        "src/nfl_forecast/fst_provenance.py",
        "src/nfl_forecast/fst_reconstruction.py",
        "src/nfl_forecast/player_state_research.py",
        "src/nfl_forecast/player_impact_engine.py",
        "src/nfl_forecast/player_impact_monitor.py",
        "src/nfl_forecast/availability_qualification.py",
        "src/nfl_forecast/availability_2025_reconstruction.py",
        "src/nfl_forecast/props_player_state.py",
        "src/nfl_forecast/props_player_sources.py",
        "src/nfl_forecast/props_contextual_intelligence.py",
        "src/nfl_forecast/props_efficiency_td.py",
        "src/nfl_forecast/props_opportunity.py",
        "src/nfl_forecast/props_opportunity_adapter.py",
        "src/nfl_forecast/props_opportunity_handoff.py",
        "src/nfl_forecast/props_market.py",
        "src/nfl_forecast/props_market_odds_api.py",
        "src/nfl_forecast/props_market_live.py",
        "src/nfl_forecast/props_manifest.py",
        "src/nfl_forecast/props_upstream.py",
        "src/nfl_forecast/props_integration.py",
        "scripts/run_challenger_v09.py",
        "scripts/run_fst_reconstruction_probe.py",
        "scripts/verify_fst_reconstruction_evidence.py",
        "scripts/build_expected_lineup_impacts.py",
        "scripts/reconstruct_2025_availability.py",
        "scripts/run_props_research_beta.py",
        "scripts/build_props_market_snapshot.py",
        "scripts/build_props_integration_manifest.py",
        "scripts/build_props_upstream_snapshot.py",
        "scripts/build_props21_challenger.py",
        "research/experiments.json",
        "research/fst/F-ST-01-FROZEN-2026.json",
        "research/player_impact/EXPECTED_LINEUP_CONTRACT.md",
        "research/availability/sources.json",
        "research/availability/2025_reconstruction_contract.json",
        "research_outputs/player_state_audit.json",
        "research_outputs/availability_2025_reconstruction/qualification.json",
        "challenger_outputs/v09_report.json",
        "tests/test_challenger_evaluation.py",
        "tests/test_fst_frozen_identity.py",
        "tests/test_player_impact_engine.py",
        "tests/test_player_impact_monitor.py",
        "tests/test_availability_qualification.py",
        "tests/test_availability_2025_reconstruction.py",
        "tests/test_props_player_state.py",
        "tests/test_props_player_sources.py",
        "tests/test_props_contextual_intelligence.py",
        "tests/test_props_efficiency_td.py",
        "tests/test_props_opportunity.py",
        "tests/test_props_opportunity_adapter.py",
        "tests/test_props_opportunity_handoff.py",
        "tests/test_props_market.py",
        "tests/test_props_market_odds_api.py",
        "tests/test_props_market_live.py",
        "tests/test_props_manifest.py",
        "tests/test_props_upstream.py",
        "tests/test_props_runner.py",
        "tests/test_props_integration.py",
        "tests/test_levline_markets_live.py",
        "tests/test_props21_coordinator.py",
        "tests/test_props21_market.py",
        "tests/test_props21_personnel.py",
        "tests/test_props21_qa.py",
        "tests/test_props21_xtd.py",
        "src/nfl_forecast/props21_market.py",
        "src/nfl_forecast/props21_personnel.py",
        "src/nfl_forecast/props21_qa.py",
        "src/nfl_forecast/props21_xtd.py",
        "site/src/Props21Challenger.jsx",
        "site/src/props21-challenger.css",
        "site/tests/props21-challenger.spec.js",
        ".github/workflows/research_firewall.yml",
        ".github/workflows/research_2025_availability_reconstruction.yml",
        ".github/workflows/levline_markets_live.yml",
        ".github/workflows/responsive.yml",
        "docs/LEVLINE_RESEARCH.md",
        "docs/IMPACT_MONITOR_GAP_ANALYSIS.md",
        "docs/FST_FREEZE_PROVENANCE.md",
    ]
    assert all(path_allowed(path) for path in allowed)
    assert validate_changed_paths(allowed) == []


def test_research_allowlist_rejects_production_surfaces():
    blocked = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/data.py",
        "src/nfl_forecast/fst_production.py",
        "src/nfl_forecast/fst_nested_pure.py",
        "src/nfl_forecast/unregistered_player_research.py",
        "src/nfl_forecast/props_unregistered_surface.py",
        "scripts/run_week.py",
        "outputs/this_week.csv",
        "outputs/prediction_history.csv",
        "site/src/AppSundaySignal.jsx",
        "pyproject.toml",
        "README.md",
    ]
    assert validate_changed_paths(blocked) == sorted(blocked)


def test_research_scope_is_detected_from_changed_surfaces_not_only_branch_name():
    assert research_scope_triggered(
        ["src/nfl_forecast/fst_provenance.py", "tests/test_fst_frozen_identity.py"],
        "fix/fst-provenance-core-current-main",
    )
    assert research_scope_triggered(["research/experiments.json"], "fix/research-plumbing")
    assert research_scope_triggered(
        ["src/nfl_forecast/unregistered_player_research.py"],
        "fix/new-player-research",
    )
    assert research_scope_triggered(
        ["src/nfl_forecast/availability_2025_reconstruction.py"],
        "fix/availability-history",
    )
    assert research_scope_triggered(
        ["src/nfl_forecast/props_unregistered_surface.py"],
        "fix/new-props-surface",
    )
    assert research_scope_triggered(["src/nfl_forecast/pipeline.py"], "research/prototype")
    assert not research_scope_triggered(["src/nfl_forecast/pipeline.py"], "fix/production-bug")
    assert not research_scope_triggered(["src/nfl_forecast/fst_production.py"], "fix/fst-production-bug")


def test_unregistered_research_path_fails_closed():
    changed = ["src/nfl_forecast/unregistered_player_research.py"]
    assert research_scope_triggered(changed, "fix/new-player-research")
    assert validate_changed_paths(changed) == changed


def test_unregistered_props_path_fails_closed():
    changed = ["src/nfl_forecast/props_unregistered_surface.py"]
    assert research_scope_triggered(changed, "fix/new-props-surface")
    assert validate_changed_paths(changed) == changed


def test_production_fst_modules_are_blocked_from_research_branches():
    changed = [
        "src/nfl_forecast/fst_provenance.py",
        "src/nfl_forecast/fst_production.py",
        "src/nfl_forecast/fst_nested_pure.py",
    ]
    assert research_scope_triggered(changed, "research/fst-provenance")
    assert validate_changed_paths(changed) == [
        "src/nfl_forecast/fst_nested_pure.py",
        "src/nfl_forecast/fst_production.py",
    ]


def test_mixed_research_and_production_diff_fails_closed():
    changed = [
        "src/nfl_forecast/fst_provenance.py",
        "research/fst/F-ST-01-FROZEN-2026.json",
        "src/nfl_forecast/pipeline.py",
    ]
    assert research_scope_triggered(changed, "fix/fst-provenance")
    assert validate_changed_paths(changed) == ["src/nfl_forecast/pipeline.py"]


def test_production_prediction_path_does_not_import_research_modules():
    protected = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/publish.py",
        "scripts/run_week.py",
    ]
    # The deployed production F-ST path legitimately imports fst_production and
    # fst_nested_pure. Research-only provenance/reconstruction/availability/Props modules
    # must remain isolated from production prediction code.
    forbidden_tokens = (
        "challenger",
        "fst_provenance",
        "fst_reconstruction",
        "experiment_registry",
        "player_state_research",
        "player_impact_cards",
        "player_impact_engine",
        "player_impact_monitor",
        "availability_qualification",
        "availability_2025_reconstruction",
        "props_player_state",
        "props_player_sources",
        "props_contextual_intelligence",
        "props_efficiency_td",
        "props_opportunity",
        "props_opportunity_adapter",
        "props_opportunity_handoff",
        "props_market",
        "props_market_odds_api",
        "props_market_live",
        "props_manifest",
        "props_upstream",
        "props_integration",
        "props21_",
    )
    for filename in protected:
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(
            token in imported
            for imported in imports
            for token in forbidden_tokens
        ), (filename, imports)
