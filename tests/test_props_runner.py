from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_props_research_beta.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_props_research_beta_tested", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload():
    return {
        "home_team": "ARI",
        "away_team": "LAR",
        "kickoff_utc": "2026-09-20T20:00:00+00:00",
        "forecast_timestamp_utc": "2026-09-17T22:00:00+00:00",
        "opportunity_projections": [{"metadata": {"game_id": "g"}}],
        "efficiency_player_parameters": [{"player_id": "p"}],
        "team_td_parameters": [{"team": "ARI"}],
        "residual_efficiency_by_team": {"ARI": {}, "LAR": {}},
        "market_artifacts": [],
        "simulations": 10,
        "seed": 1,
    }


def _patch_pipeline(monkeypatch, module, events, *, fail_lock=False):
    monkeypatch.setattr(module, "build_game_input_from_upstream", lambda **kwargs: "game")
    monkeypatch.setattr(module, "simulate_game", lambda game, simulations, seed: "result")
    monkeypatch.setattr(
        module,
        "build_forecast_artifact",
        lambda result, markets, **kwargs: {
            "contract_version": "levline-props-forecast-v0.1",
            "generated_utc": "2026-09-17T22:00:00+00:00",
            "forecasts": [{"forecast_id": "f1"}],
        },
    )
    monkeypatch.setattr(
        module,
        "build_public_props",
        lambda artifact, now_utc: {"contract_version": "levline-props-public-v0.1"},
    )
    monkeypatch.setattr(
        module,
        "make_forecast_receipt",
        lambda row, recorded_utc: {"forecast_id": row["forecast_id"]},
    )

    def lock(path, receipts, identity_key):
        events.append(("lock", str(path), identity_key))
        if fail_lock:
            raise RuntimeError("immutable collision")
        return 1

    def write(path, payload):
        events.append(("write", str(path), payload["contract_version"]))

    monkeypatch.setattr(module, "append_jsonl_immutable", lock)
    monkeypatch.setattr(module, "_write_json", write)


def test_producer_locks_originals_before_any_publication(monkeypatch, tmp_path):
    module = _module()
    events = []
    _patch_pipeline(monkeypatch, module, events)

    module.produce(
        _payload(),
        output=tmp_path / "forecasts.json",
        public_output=tmp_path / "public_props.json",
        history_ledger=tmp_path / "forecast_originals.jsonl",
    )

    assert events[0][0] == "lock"
    assert [event[0] for event in events] == ["lock", "write", "write"]


def test_lock_failure_leaves_no_forecast_or_public_artifact(monkeypatch, tmp_path):
    module = _module()
    events = []
    _patch_pipeline(monkeypatch, module, events, fail_lock=True)

    with pytest.raises(RuntimeError, match="immutable collision"):
        module.produce(
            _payload(),
            output=tmp_path / "forecasts.json",
            public_output=tmp_path / "public_props.json",
            history_ledger=tmp_path / "forecast_originals.jsonl",
        )

    assert [event[0] for event in events] == ["lock"]
