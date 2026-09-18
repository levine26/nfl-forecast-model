from __future__ import annotations

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
