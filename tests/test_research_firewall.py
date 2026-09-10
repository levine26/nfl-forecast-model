from __future__ import annotations

import ast
from pathlib import Path

from scripts.check_research_firewall import path_allowed, validate_changed_paths


def test_research_allowlist_accepts_isolated_surfaces():
    allowed = [
        "src/nfl_forecast/challenger_evaluation.py",
        "src/nfl_forecast/challenger_v09.py",
        "src/nfl_forecast/player_state_research.py",
        "scripts/run_challenger_v09.py",
        "research/experiments.json",
        "research_outputs/player_state_audit.json",
        "challenger_outputs/v09_report.json",
        "tests/test_challenger_evaluation.py",
        ".github/workflows/research_firewall.yml",
        "docs/LEVLINE_RESEARCH.md",
    ]
    assert all(path_allowed(path) for path in allowed)
    assert validate_changed_paths(allowed) == []


def test_research_allowlist_rejects_production_surfaces():
    blocked = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/data.py",
        "scripts/run_week.py",
        "outputs/this_week.csv",
        "outputs/prediction_history.csv",
        "site/src/AppSundaySignal.jsx",
        "pyproject.toml",
        "README.md",
    ]
    assert validate_changed_paths(blocked) == sorted(blocked)


def test_production_prediction_path_does_not_import_research_modules():
    protected = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/publish.py",
        "scripts/run_week.py",
    ]
    forbidden_tokens = (
        "challenger",
        "experiment_registry",
        "player_state_research",
        "player_impact_cards",
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
