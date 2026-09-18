from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from nfl_forecast.props_manifest import (
    MANIFEST_CONTRACT_VERSION,
    PropsManifestError,
    assemble_manifest,
    payload_sha256,
    verify_manifest_fingerprint,
)


GAME_ID = "2026_03_LAR_ARI"
FORECAST = "2026-09-20T16:05:00Z"
KICKOFF = "2026-09-20T20:05:00Z"


def _projection(team: str, opponent: str) -> dict:
    return {
        "metadata": {
            "game_id": GAME_ID,
            "season": 2026,
            "week": 3,
            "team": team,
            "opponent": opponent,
            "forecast_timestamp": "2026-09-20T16:00:00Z",
            "data_horizon": "2026-09-20T15:55:00Z",
        },
        "hierarchy": {},
        "marginals": {},
        "players": [],
        "redistribution": {},
        "audit": {},
    }


def _efficiency_row(team: str, opponent: str, player_id: str) -> dict:
    return {
        "game_id": GAME_ID,
        "season": 2026,
        "week": 3,
        "team": team,
        "opponent": opponent,
        "player_id": player_id,
        "forecast_timestamp": "2026-09-20T16:00:00Z",
        "feature_data_horizon": "2026-09-20T15:55:00Z",
        "kickoff_timestamp": KICKOFF,
        "prior_model_trained_through_season": 2025,
    }


def _team_td_row(team: str, opponent: str) -> dict:
    return {
        "game_id": GAME_ID,
        "season": 2026,
        "week": 3,
        "team": team,
        "opponent": opponent,
        "forecast_timestamp": "2026-09-20T16:00:00Z",
        "feature_data_horizon": "2026-09-20T15:55:00Z",
        "kickoff_timestamp": KICKOFF,
        "prior_model_trained_through_season": 2025,
    }


def _market_snapshot() -> dict:
    return {
        "contract_version": "levline-props-market-snapshot-v0.1",
        "captured_at_utc": "2026-09-20T16:02:00Z",
        "market_artifacts": [
            {
                "game_id": GAME_ID,
                "player_id": "QB1",
                "prop_type": "passing_yards",
                "as_of_utc": "2026-09-20T16:02:00Z",
                "closing_evaluation": None,
            }
        ],
    }


def _assemble(**overrides):
    kwargs = {
        "game_spec": {
            "home_team": "ARI",
            "away_team": "LAR",
            "kickoff_utc": KICKOFF,
            "forecast_timestamp_utc": FORECAST,
            "simulations": 20000,
            "seed": 7,
        },
        "opportunity_projections": [
            _projection("ARI", "LAR"),
            _projection("LAR", "ARI"),
        ],
        "efficiency_player_parameters": [
            _efficiency_row("ARI", "LAR", "QB1"),
            _efficiency_row("LAR", "ARI", "QB2"),
        ],
        "team_td_parameters": [
            _team_td_row("ARI", "LAR"),
            _team_td_row("LAR", "ARI"),
        ],
        "residual_efficiency_by_team": {
            "ARI": {"receiving_ypr_mean": 10.0},
            "LAR": {"receiving_ypr_mean": 10.0},
        },
        "market_snapshot": _market_snapshot(),
        "input_provenance": {"market_snapshot": {"sha256": "abc"}},
    }
    kwargs.update(overrides)
    return assemble_manifest(**kwargs)


def test_manifest_assembler_validates_and_preserves_frozen_components():
    manifest = _assemble()
    assert manifest["manifest_contract_version"] == MANIFEST_CONTRACT_VERSION
    assert manifest["game_id"] == GAME_ID
    assert manifest["home_team"] == "ARI"
    assert manifest["away_team"] == "LAR"
    assert manifest["simulations"] == 20000
    assert manifest["seed"] == 7
    assert manifest["market_artifacts"][0]["player_id"] == "QB1"
    assert manifest["input_provenance"]["market_snapshot"]["sha256"] == "abc"


def test_market_snapshot_newer_than_manifest_forecast_fails_closed():
    market = _market_snapshot()
    market["captured_at_utc"] = "2026-09-20T16:06:00Z"
    with pytest.raises(PropsManifestError, match="newer"):
        _assemble(market_snapshot=market)


def test_completed_2026_efficiency_prior_fails_closed():
    rows = [
        _efficiency_row("ARI", "LAR", "QB1"),
        _efficiency_row("LAR", "ARI", "QB2"),
    ]
    rows[0]["prior_model_trained_through_season"] = 2026
    with pytest.raises(PropsManifestError, match="completed 2026"):
        _assemble(efficiency_player_parameters=rows)


def test_mismatched_opportunity_game_or_team_fails_closed():
    projections = [
        _projection("ARI", "LAR"),
        _projection("SEA", "ARI"),
    ]
    with pytest.raises(PropsManifestError, match="do not match"):
        _assemble(opportunity_projections=projections)


def test_duplicate_market_identity_fails_closed():
    market = _market_snapshot()
    market["market_artifacts"].append(dict(market["market_artifacts"][0]))
    with pytest.raises(PropsManifestError, match="duplicate market artifact"):
        _assemble(market_snapshot=market)


def test_closing_evaluation_cannot_enter_prospective_manifest():
    market = _market_snapshot()
    market["market_artifacts"][0]["closing_evaluation"] = {"line": 250.5}
    with pytest.raises(PropsManifestError, match="closing evaluation"):
        _assemble(market_snapshot=market)


def test_payload_hash_is_deterministic_across_mapping_order():
    assert payload_sha256({"a": 1, "b": 2}) == payload_sha256({"b": 2, "a": 1})


def test_manifest_fingerprint_detects_tampering():
    manifest = _assemble()
    manifest["manifest_sha256"] = payload_sha256(manifest)
    verify_manifest_fingerprint(manifest)

    tampered = dict(manifest)
    tampered["seed"] = 999
    with pytest.raises(PropsManifestError, match="fingerprint mismatch"):
        verify_manifest_fingerprint(tampered)


def test_slate_wide_market_snapshot_selects_only_target_game():
    market = _market_snapshot()
    market["market_artifacts"].append(
        {
            "game_id": "2026_03_BUF_MIA",
            "player_id": "OTHER",
            "prop_type": "passing_yards",
            "as_of_utc": "2026-09-20T16:02:00Z",
            "closing_evaluation": None,
        }
    )
    manifest = _assemble(market_snapshot=market)
    assert len(manifest["market_artifacts"]) == 1
    assert manifest["market_artifacts"][0]["game_id"] == GAME_ID


def test_residual_team_aliases_are_canonicalized():
    manifest = _assemble(
        residual_efficiency_by_team={
            "ARI": {"receiving_ypr_mean": 10.0},
            "LAR": {"receiving_ypr_mean": 10.0},
        }
    )
    assert set(manifest["residual_efficiency_by_team"]) == {"ARI", "LAR"}



ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCRIPT = ROOT / "scripts" / "build_props_integration_manifest.py"


def _manifest_builder_module():
    spec = importlib.util.spec_from_file_location(
        "build_props_integration_manifest_tested",
        MANIFEST_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _game_payloads(game_id, home, away, kickoff=KICKOFF):
    def projection(team, opponent):
        return {
            "metadata": {
                "game_id": game_id,
                "season": 2026,
                "week": 3,
                "team": team,
                "opponent": opponent,
                "forecast_timestamp": "2026-09-20T16:00:00Z",
                "data_horizon": "2026-09-20T15:55:00Z",
            },
            "hierarchy": {},
            "marginals": {},
            "players": [],
            "redistribution": {},
            "audit": {},
        }

    def eff(team, opponent, player_id):
        return {
            "game_id": game_id,
            "season": 2026,
            "week": 3,
            "team": team,
            "opponent": opponent,
            "player_id": player_id,
            "forecast_timestamp": "2026-09-20T16:00:00Z",
            "feature_data_horizon": "2026-09-20T15:55:00Z",
            "kickoff_timestamp": kickoff,
            "prior_model_trained_through_season": 2025,
        }

    def td(team, opponent):
        return {
            "game_id": game_id,
            "season": 2026,
            "week": 3,
            "team": team,
            "opponent": opponent,
            "forecast_timestamp": "2026-09-20T16:00:00Z",
            "feature_data_horizon": "2026-09-20T15:55:00Z",
            "kickoff_timestamp": kickoff,
            "prior_model_trained_through_season": 2025,
        }

    return {
        "game_spec": {
            "game_id": game_id,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": kickoff,
        },
        "opportunity": {
            "opportunity_projections": [
                projection(home, away),
                projection(away, home),
            ]
        },
        "efficiency_player": {
            "efficiency_player_parameters": [
                eff(home, away, f"{home}-QB"),
                eff(away, home, f"{away}-QB"),
            ]
        },
        "team_td": {
            "team_td_parameters": [
                td(home, away),
                td(away, home),
            ]
        },
        "residual_efficiency": {
            "residual_efficiency_by_team": {
                home: {"receiving_ypr_mean": 10.0},
                away: {"receiving_ypr_mean": 10.0},
            }
        },
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _upstream_slate_fixture(tmp_path, *, poison_second=False):
    root = tmp_path / "upstream"
    games = [
        ("2026_03_ARI_LA", "ARI", "LAR"),
        ("2026_03_BUF_MIA", "BUF", "MIA"),
    ]
    entries = []
    for index, (game_id, home, away) in enumerate(games):
        payloads = _game_payloads(game_id, home, away)
        if poison_second and index == 1:
            payloads["team_td"]["team_td_parameters"][0][
                "prior_model_trained_through_season"
            ] = 2026
        game_root = root / "games" / game_id
        files = {}
        for key, payload in payloads.items():
            path = game_root / f"{game_id}.{key}.json"
            _write_json(path, payload)
            files[key] = str(path.relative_to(root))
        entries.append(
            {
                "game_id": game_id,
                "home_team": home,
                "away_team": away,
                "kickoff_utc": KICKOFF,
                "files": files,
            }
        )
    upstream = {
        "contract_version": "levline-props-upstream-slate-v0.1",
        "research_only": True,
        "production_authorized": False,
        "game_count": len(entries),
        "games": entries,
    }
    index_path = root / "upstream_slate.json"
    _write_json(index_path, upstream)

    market = {
        "contract_version": "levline-props-market-snapshot-v0.1",
        "captured_at_utc": "2026-09-20T16:02:00Z",
        "market_artifacts": [
            {
                "game_id": game_id,
                "player_id": f"{home}-QB",
                "prop_type": "passing_yards",
                "as_of_utc": "2026-09-20T16:02:00Z",
                "closing_evaluation": None,
            }
            for game_id, home, _ in games
        ],
    }
    market_path = tmp_path / "market_snapshot.json"
    _write_json(market_path, market)
    return index_path, market_path


def _slate_args(index_path, market_path, output_dir):
    return SimpleNamespace(
        upstream_slate=index_path,
        game_spec=None,
        opportunity=None,
        efficiency_player=None,
        team_td=None,
        residual_efficiency=None,
        market_snapshot=market_path,
        output=None,
        output_dir=output_dir,
        forecast_timestamp="2026-09-20T16:05:00Z",
    )


def test_slate_manifest_builder_uses_one_freeze_and_one_market_fingerprint(tmp_path):
    module = _manifest_builder_module()
    index_path, market_path = _upstream_slate_fixture(tmp_path)
    output_dir = tmp_path / "manifests"
    args = _slate_args(index_path, market_path, output_dir)
    raw_market = module._load(market_path)
    freeze = module._forecast_timestamp(args.forecast_timestamp)

    assert module._slate_mode(args, raw_market, freeze) == 0

    index = json.loads((output_dir / "manifest_slate.json").read_text())
    assert index["game_count"] == 2
    assert index["forecast_timestamp_utc"] == "2026-09-20T16:05:00+00:00"
    market_sha = index["market_snapshot"]["sha256"]
    for row in index["games"]:
        manifest = json.loads(
            (output_dir / row["manifest_file"]).read_text(encoding="utf-8")
        )
        assert manifest["forecast_timestamp_utc"] == index["forecast_timestamp_utc"]
        assert (
            manifest["input_provenance"]["market_snapshot"]["sha256"]
            == market_sha
        )
        verify_manifest_fingerprint(manifest)


def test_slate_manifest_builder_failure_writes_nothing(tmp_path):
    module = _manifest_builder_module()
    index_path, market_path = _upstream_slate_fixture(
        tmp_path,
        poison_second=True,
    )
    output_dir = tmp_path / "manifests"
    args = _slate_args(index_path, market_path, output_dir)

    with pytest.raises(PropsManifestError, match="completed 2026"):
        module._slate_mode(
            args,
            module._load(market_path),
            module._forecast_timestamp(args.forecast_timestamp),
        )

    assert not output_dir.exists()


def test_slate_manifest_builder_rejects_index_path_escape(tmp_path):
    module = _manifest_builder_module()
    index_path, market_path = _upstream_slate_fixture(tmp_path)
    upstream = json.loads(index_path.read_text(encoding="utf-8"))
    upstream["games"][0]["files"]["game_spec"] = "../../outside.json"
    index_path.write_text(json.dumps(upstream), encoding="utf-8")
    args = _slate_args(index_path, market_path, tmp_path / "manifests")

    with pytest.raises(ValueError, match="escapes its root"):
        module._slate_mode(
            args,
            module._load(market_path),
            module._forecast_timestamp(args.forecast_timestamp),
        )


def test_slate_manifest_builder_preflights_all_outputs_before_write(tmp_path):
    module = _manifest_builder_module()
    index_path, market_path = _upstream_slate_fixture(tmp_path)
    output_dir = tmp_path / "manifests"
    existing = output_dir / "games" / "2026_03_BUF_MIA.manifest.json"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("do-not-touch", encoding="utf-8")
    args = _slate_args(index_path, market_path, output_dir)

    with pytest.raises(FileExistsError, match="refusing partial overwrite"):
        module._slate_mode(
            args,
            module._load(market_path),
            module._forecast_timestamp(args.forecast_timestamp),
        )

    assert not (
        output_dir / "games" / "2026_03_ARI_LA.manifest.json"
    ).exists()
    assert existing.read_text(encoding="utf-8") == "do-not-touch"
