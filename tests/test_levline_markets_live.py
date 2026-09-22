from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_levline_markets_live.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_levline_markets_live_tested", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_target_week_requires_one_canonical_period(tmp_path):
    module = _module()
    slate = tmp_path / "this_week.csv"
    slate.write_text(
        "game_id,season,week\n"
        "g1,2026,2\n"
        "g2,2026,2\n",
        encoding="utf-8",
    )
    assert module.resolve_target_week(slate) == (2026, 2)

    slate.write_text(
        "game_id,season,week\n"
        "g1,2026,2\n"
        "g2,2026,3\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exactly one season/week"):
        module.resolve_target_week(slate)


def test_validate_priors_requires_explicit_route_and_unknown_availability(tmp_path):
    module = _module()
    priors = tmp_path / "priors.json"
    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 0.90, "TE": 0.75},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 9.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    loaded = module.validate_priors(priors)
    assert loaded["route_prior_means"]["WR"] == 0.90

    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 0.90},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 9.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing TE"):
        module.validate_priors(priors)


def test_validate_priors_rejects_implicit_or_invalid_unknown_prior(tmp_path):
    module = _module()
    priors = tmp_path / "priors.json"
    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 0.90, "TE": 0.75},
                "availability_beta_priors": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="availability_beta_priors.UNKNOWN"):
        module.validate_priors(priors)

    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 1.2, "TE": 0.75},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 9.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="within"):
        module.validate_priors(priors)


def test_repository_frozen_priors_are_preregistered_and_valid():
    module = _module()
    priors_path = ROOT / "config" / "levline_markets_priors_v1.json"
    payload = module.validate_priors(priors_path)
    assert payload["contract_version"] == "levline-markets-priors-v1"
    assert payload["governance"]["frozen_before_first_live_production_cycle"] is True
    assert payload["governance"]["completed_2026_outcomes_used_for_selection"] is False
    assert payload["governance"]["props_evaluation_results_used_for_selection"] is False
    assert payload["route_prior_means"] == {"RB": 0.55, "WR": 0.90, "TE": 0.75}
    assert payload["availability_beta_priors"]["UNKNOWN"] == {
        "alpha": 9.0,
        "beta": 1.0,
    }


def test_live_coordinator_uses_sharded_permanent_history_append():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "append_jsonl_immutable_sharded" in text
    assert (
        'append_jsonl_immutable_sharded(permanent_ledger, receipts, identity_key="forecast_id")'
        in text
    )
    assert (
        'append_jsonl_immutable(permanent_ledger, receipts, identity_key="forecast_id")'
        not in text
    )


def test_live_workflow_transports_frozen_depth_chart_personnel_snapshot():
    workflow = (ROOT / ".github" / "workflows" / "levline_markets_live.yml").read_text(
        encoding="utf-8"
    )
    assert 'DEPTH_CHARTS="$RUN_ROOT/upstream/depth_charts.json"' in workflow
    assert '--depth-charts "$DEPTH_CHARTS"' in workflow
    assert 'DEPTH_CHARTS_SHA=$(sha256sum "$DEPTH_CHARTS"' in workflow
    assert 'depth_charts_sha256:$depth_charts_sha256' in workflow


def test_live_workflow_allows_clean_postkickoff_noop():
    workflow = (ROOT / ".github" / "workflows" / "levline_markets_live.yml").read_text(
        encoding="utf-8"
    )
    assert "--allow-empty-postkickoff" in workflow
    assert "postkickoff_noop.json" in workflow
    assert "Props live refresh no-op: target week has no pregame games remaining." in workflow


def test_live_workflow_captures_props22_from_current_run_props21_json():
    workflow = (ROOT / ".github" / "workflows" / "levline_markets_live.yml").read_text(
        encoding="utf-8"
    )
    assert "research/props/v22/capture_prospective.py" in workflow
    assert "--source-json challenger_outputs/props21/public_challenger.json" in workflow
    assert "--output challenger_outputs/props22/forecast_originals.jsonl" in workflow
    assert "challenger_outputs/props22" in workflow
    assert "research/props/v22/test_capture_prospective.py" in workflow


def test_live_coordinator_postkickoff_noop_preserves_existing_publication(monkeypatch, tmp_path):
    module = _module()
    priors = tmp_path / "priors.json"
    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 0.90, "TE": 0.75},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 9.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "published"
    output_root.mkdir()
    sentinel = output_root / "forecasts.json"
    sentinel.write_text('{"sentinel":"prior-valid-publication"}\n', encoding="utf-8")
    work_root = tmp_path / "work"

    calls = []

    def fake_run(*args):
        calls.append([str(value) for value in args])
        command = calls[-1]
        assert "build_props_upstream_snapshot.py" in " ".join(command)
        output_dir = Path(command[command.index("--output-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "postkickoff_noop.json").write_text(
            json.dumps(
                {
                    "contract_version": "levline-props-postkickoff-noop-v0.1",
                    "season": 2026,
                    "week": 2,
                    "pregame_game_ids": [],
                    "started_game_ids": ["g1", "g2"],
                    "reason": "target week has no scheduled pregame games remaining",
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setenv("THE_ODDS_API_KEY", "test-key")
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        [
            str(SCRIPT),
            "--season",
            "2026",
            "--week",
            "2",
            "--priors",
            str(priors),
            "--work-root",
            str(work_root),
            "--output-root",
            str(output_root),
            "--allow-empty-postkickoff",
        ],
    )

    assert module.main() == 0
    assert len(calls) == 1
    assert "--allow-empty-postkickoff" in calls[0]
    assert sentinel.read_text(encoding="utf-8") == '{"sentinel":"prior-valid-publication"}\n'
