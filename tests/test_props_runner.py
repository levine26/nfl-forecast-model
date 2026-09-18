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



def test_multi_game_producer_locks_full_slate_before_publication(monkeypatch, tmp_path):
    module = _module()
    events = []
    counter = iter(["f1", "f2"])

    monkeypatch.setattr(module, "build_game_input_from_upstream", lambda **kwargs: "game")
    monkeypatch.setattr(module, "simulate_game", lambda game, simulations, seed: "result")

    def build_artifact(result, markets, **kwargs):
        forecast_id = next(counter)
        return {
            "contract_version": "levline-props-forecast-v0.1",
            "generated_utc": "2026-09-17T22:00:00+00:00",
            "research_label": "LEVLINE PROPS — RESEARCH BETA",
            "scope": "OFFENSIVE_PROPS_ONLY",
            "forecasts": [
                {
                    "forecast_id": forecast_id,
                    "kickoff_utc": "2026-09-20T20:00:00+00:00",
                    "forecast_timestamp_utc": "2026-09-17T22:00:00+00:00",
                    "signal_state": "NO SIGNAL",
                    "market": {"captured_utc": None},
                }
            ],
        }

    monkeypatch.setattr(module, "build_forecast_artifact", build_artifact)

    public_seen = {}

    def build_public(artifact, now_utc):
        public_seen["forecast_count"] = len(artifact["forecasts"])
        public_seen["game_count"] = artifact["game_count"]
        return {"contract_version": "levline-props-public-v0.1"}

    monkeypatch.setattr(module, "build_public_props", build_public)
    monkeypatch.setattr(
        module,
        "make_forecast_receipt",
        lambda row, recorded_utc: {"forecast_id": row["forecast_id"]},
    )

    def lock(path, receipts, identity_key):
        receipts = list(receipts)
        events.append(("lock", len(receipts), identity_key))
        return len(receipts)

    def write(path, payload):
        events.append(("write", str(path), payload["contract_version"]))

    monkeypatch.setattr(module, "append_jsonl_immutable", lock)
    monkeypatch.setattr(module, "_write_json", write)

    second = dict(_payload())
    second["home_team"] = "BUF"
    second["away_team"] = "MIA"
    artifact = module.produce_many(
        [_payload(), second],
        output=tmp_path / "forecasts.json",
        public_output=tmp_path / "public_props.json",
        history_ledger=tmp_path / "forecast_originals.jsonl",
    )

    assert artifact["game_count"] == 2
    assert len(artifact["forecasts"]) == 2
    assert public_seen == {"forecast_count": 2, "game_count": 2}
    assert events[0] == ("lock", 2, "forecast_id")
    assert [event[0] for event in events] == ["lock", "write", "write"]


def test_multi_game_build_failure_publishes_nothing(monkeypatch, tmp_path):
    module = _module()
    events = []
    calls = {"count": 0}
    monkeypatch.setattr(module, "build_game_input_from_upstream", lambda **kwargs: "game")
    monkeypatch.setattr(module, "simulate_game", lambda game, simulations, seed: "result")

    def build_artifact(result, markets, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("second game failed")
        return {
            "contract_version": "levline-props-forecast-v0.1",
            "generated_utc": "2026-09-17T22:00:00+00:00",
            "research_label": "LEVLINE PROPS — RESEARCH BETA",
            "scope": "OFFENSIVE_PROPS_ONLY",
            "forecasts": [{"forecast_id": "f1"}],
        }

    monkeypatch.setattr(module, "build_forecast_artifact", build_artifact)
    monkeypatch.setattr(
        module,
        "append_jsonl_immutable",
        lambda *args, **kwargs: events.append(("lock",)),
    )
    monkeypatch.setattr(
        module,
        "_write_json",
        lambda *args, **kwargs: events.append(("write",)),
    )

    with pytest.raises(RuntimeError, match="second game failed"):
        module.produce_many(
            [_payload(), _payload()],
            output=tmp_path / "forecasts.json",
            public_output=tmp_path / "public_props.json",
            history_ledger=tmp_path / "forecast_originals.jsonl",
        )
    assert events == []


def test_slate_rejects_duplicate_forecast_ids_before_history_lock(monkeypatch, tmp_path):
    module = _module()
    events = []
    monkeypatch.setattr(module, "build_game_input_from_upstream", lambda **kwargs: "game")
    monkeypatch.setattr(module, "simulate_game", lambda game, simulations, seed: "result")
    monkeypatch.setattr(
        module,
        "build_forecast_artifact",
        lambda result, markets, **kwargs: {
            "contract_version": "levline-props-forecast-v0.1",
            "generated_utc": "2026-09-17T22:00:00+00:00",
            "research_label": "LEVLINE PROPS — RESEARCH BETA",
            "scope": "OFFENSIVE_PROPS_ONLY",
            "forecasts": [{"forecast_id": "same"}],
        },
    )
    monkeypatch.setattr(
        module,
        "append_jsonl_immutable",
        lambda *args, **kwargs: events.append(("lock",)),
    )
    monkeypatch.setattr(
        module,
        "_write_json",
        lambda *args, **kwargs: events.append(("write",)),
    )

    with pytest.raises(ValueError, match="duplicate forecast_id"):
        module.produce_many(
            [_payload(), _payload()],
            output=tmp_path / "forecasts.json",
            public_output=None,
            history_ledger=tmp_path / "forecast_originals.jsonl",
        )
    assert events == []
