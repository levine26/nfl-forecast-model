from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"record_prospective_football_shadow.py"
FROZEN=ROOT/"research"/"props"/"v2"/"DEFENSIVE_EFFICIENCY_SHADOW_FROZEN.json"


def _module():
    spec=importlib.util.spec_from_file_location("football_shadow_tested",SCRIPT)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pbp():
    rows=[]
    for week in (1,2,3):
        for defense in ("ARI","LAR"):
            offense="LAR" if defense=="ARI" else "ARI"
            for i in range(6):
                rows.append({
                    "game_id":f"2025_{week}_{offense}_{defense}",
                    "season":2025,
                    "week":week,
                    "season_type":"REG",
                    "defteam":defense,
                    "rush_attempt":1,
                    "complete_pass":0,
                    "qb_scramble":0,
                    "rusher_player_id":"RB1" if offense=="ARI" else "RB2",
                    "receiver_player_id":None,
                    "rushing_yards":4.0+(1.0 if defense=="LAR" else -0.5)+(100.0 if week==3 else 0.0),
                    "receiving_yards":np.nan,
                    "yards_gained":4.0,
                })
            for i in range(5):
                rows.append({
                    "game_id":f"2025_{week}_{offense}_{defense}",
                    "season":2025,
                    "week":week,
                    "season_type":"REG",
                    "defteam":defense,
                    "rush_attempt":0,
                    "complete_pass":1,
                    "qb_scramble":0,
                    "rusher_player_id":None,
                    "receiver_player_id":"WR1" if offense=="ARI" else "WR2",
                    "rushing_yards":np.nan,
                    "receiving_yards":9.0+(2.0 if defense=="LAR" else -1.0)+(100.0 if week==3 else 0.0),
                    "yards_gained":9.0,
                })
    return pd.DataFrame(rows)


def test_frozen_coefficients_are_pre2026_and_research_only():
    module=_module()
    frozen=module.load_frozen_coefficients(FROZEN)
    assert frozen["trained_through_season"]==2025
    assert frozen["production_authorized"] is False
    assert frozen["fits"]["rushing"]["beta_standardized"]==pytest.approx(0.1060375269278496)
    assert frozen["fits"]["receiving"]["beta_standardized"]==pytest.approx(0.21008097583610338)


def test_defense_state_is_strict_prior_week(monkeypatch):
    module=_module()
    monkeypatch.setattr(
        module,
        "_player_positions",
        lambda: {"RB1":"RB","RB2":"RB","WR1":"WR","WR2":"WR"},
    )
    pbp=_pbp()
    state,_=module.build_defense_state(
        pbp,target_season=2025,target_week=3,teams={"ARI","LAR"}
    )
    mutated=pbp.copy()
    mutated.loc[mutated["week"].eq(3),"rushing_yards"]=9999.0
    mutated.loc[mutated["week"].eq(3),"receiving_yards"]=9999.0
    state2,_=module.build_defense_state(
        mutated,target_season=2025,target_week=3,teams={"ARI","LAR"}
    )
    assert state==state2
    assert state["LAR"]["rushing"]["opponent_defense_delta"] > state["ARI"]["rushing"]["opponent_defense_delta"]
    assert state["LAR"]["receiving"]["opponent_defense_delta"] > state["ARI"]["receiving"]["opponent_defense_delta"]


def test_adjusted_mean_uses_frozen_standardized_residual():
    module=_module()
    fit={
        "x_mean":0.0,
        "x_sd":0.5,
        "intercept":-0.1,
        "beta_standardized":0.2,
    }
    assert module.adjusted_mean(4.5,0.5,fit)==pytest.approx(4.6)
    assert module.adjusted_mean(4.5,-0.5,fit)==pytest.approx(4.2)


@dataclass(frozen=True)
class DummyResult:
    game_id: str
    model_version: str
    players: tuple
    player_stats: dict


def test_shadow_overlay_preserves_all_opportunity_arrays():
    module=_module()
    player=SimpleNamespace(
        player_id="P1",
        opponent="LAR",
        rushing_yards_per_carry=4.3,
        rushing_yards_shape_per_carry=2.0,
        rushing_yards_per_carry_event_sd=3.0,
        rushing_yards_per_carry_mean_se=0.1,
        receiving_yards_per_reception=10.0,
        receiving_yards_shape_per_reception=2.0,
        receiving_yards_per_reception_event_sd=5.0,
        receiving_yards_per_reception_mean_se=0.1,
    )
    n=200
    stats={
        "active":np.ones(n,dtype=int),
        "pass_attempts":np.zeros(n,dtype=int),
        "routes":np.arange(n)%20,
        "targets":np.arange(n)%8,
        "receptions":np.arange(n)%6,
        "carries":np.arange(n)%12,
        "rushing_yards":np.zeros(n,dtype=int),
        "receiving_yards":np.zeros(n,dtype=int),
    }
    baseline=DummyResult(
        game_id="G1",
        model_version="V1",
        players=(player,),
        player_stats={"P1":{k:v.copy() for k,v in stats.items()}},
    )
    frozen=module.load_frozen_coefficients(FROZEN)
    defense={
        "LAR":{
            "rushing":{"opponent_defense_delta":0.3},
            "receiving":{"opponent_defense_delta":0.5},
        }
    }
    shadow,audit=module.apply_shadow_a(
        baseline,defense_state=defense,frozen=frozen
    )
    assert shadow.model_version==module.SHADOW_VERSION
    for key in module.OPPORTUNITY_KEYS:
        assert np.array_equal(
            baseline.player_stats["P1"][key],
            shadow.player_stats["P1"][key],
        )
    assert not np.array_equal(
        baseline.player_stats["P1"]["rushing_yards"],
        shadow.player_stats["P1"]["rushing_yards"],
    )
    assert audit["P1"]["shadow_rushing_yards_per_carry"] != pytest.approx(4.3)


def test_receipt_fails_closed_after_kickoff():
    module=_module()
    frozen=module.load_frozen_coefficients(FROZEN)
    source={
        "forecast_id":"f1",
        "game_id":"G1",
        "player_id":"P1",
        "player":"Player",
        "position":"RB",
        "team":"ARI",
        "opponent":"LAR",
        "prop_type":"rushing_yards",
        "kickoff_utc":"2026-09-20T20:00:00+00:00",
        "forecast_timestamp_utc":"2026-09-20T18:00:00+00:00",
        "data_horizon_utc":"2026-09-20T17:59:00+00:00",
        "signal_state":"WATCH",
        "data_quality":{"state":"HIGH","critical_ok":True,"confidence":"HIGH","notes":[]},
        "market":{
            "captured_utc":"2026-09-20T18:00:00+00:00",
            "line":60.5,
            "no_vig_over_probability":0.51,
            "over_price_american":-110,
            "under_price_american":-110,
        },
        "model":{
            "version":"V1","fair_line":62.0,"over_probability":0.54,
            "under_probability":0.46,"standard_deviation":20.0,
            "prediction_interval":{"low":30,"high":90,"coverage":0.8},
        },
    }
    shadow=json.loads(json.dumps(source))
    shadow["model"]["version"]=module.SHADOW_VERSION
    shadow["model"]["fair_line"]=63.0
    manifest={"manifest_sha256":"a"*64}
    audit={
        "base_rushing_yards_per_carry":4.2,
        "shadow_rushing_yards_per_carry":4.4,
        "rushing_defense_state":{"opponent_defense_delta":0.2},
        "base_receiving_yards_per_reception":10.0,
        "shadow_receiving_yards_per_reception":10.1,
        "receiving_defense_state":{"opponent_defense_delta":0.1},
    }
    before=datetime(2026,9,20,19,0,tzinfo=timezone.utc)
    receipt=module.build_receipt(
        source=source,shadow=shadow,manifest=manifest,player_audit={"P1":audit},
        frozen=frozen,recorded_utc=before,source_workflow_run="1",source_head_sha="b"*40,
        source_season=2026,source_week=2,
        v1_samples=np.array([40,50,60,70,80],dtype=float),
        shadow_samples=np.array([42,52,62,72,82],dtype=float),
    )
    assert receipt is not None
    assert receipt["recorded_utc"]==before.isoformat()
    assert receipt["governance"]["production_authorized"] is False
    assert receipt["source_signal_state"]=="WATCH"
    assert receipt["source_data_quality"]["state"]=="HIGH"
    assert receipt["source_data_horizon_utc"]=="2026-09-20T17:59:00+00:00"
    assert receipt["source_season"]==2026
    assert receipt["source_week"]==2
    assert receipt["v1"]["empirical_distribution"]["sample_count"]==5
    assert sum(receipt["v1"]["empirical_distribution"]["counts"])==5
    assert receipt["shadow_a"]["empirical_distribution"]["sample_count"]==5
    assert len(receipt["v1"]["empirical_distribution"]["sha256"])==64
    after=datetime(2026,9,20,21,0,tzinfo=timezone.utc)
    assert module.build_receipt(
        source=source,shadow=shadow,manifest=manifest,player_audit={"P1":audit},
        frozen=frozen,recorded_utc=after,source_workflow_run="1",source_head_sha="b"*40,
        source_season=2026,source_week=2,
        v1_samples=np.array([40,50,60,70,80],dtype=float),
        shadow_samples=np.array([42,52,62,72,82],dtype=float),
    ) is None


def test_marketless_v1_row_is_ineligible_not_fatal():
    module=_module()
    frozen=module.load_frozen_coefficients(FROZEN)
    source={
        "forecast_id":"f-no-market",
        "game_id":"G1",
        "player_id":"P1",
        "player":"Player",
        "position":"RB",
        "team":"ARI",
        "opponent":"LAR",
        "prop_type":"rushing_yards",
        "kickoff_utc":"2026-09-20T20:00:00+00:00",
        "forecast_timestamp_utc":"2026-09-20T18:00:00+00:00",
        "market":{
            "captured_utc":None,
            "line":None,
            "no_vig_over_probability":None,
        },
        "model":{
            "version":"V1",
            "fair_line":62.0,
            "over_probability":None,
            "under_probability":None,
        },
    }
    shadow=json.loads(json.dumps(source))
    shadow["model"]["version"]=module.SHADOW_VERSION
    audit={
        "base_rushing_yards_per_carry":4.2,
        "shadow_rushing_yards_per_carry":4.4,
        "rushing_defense_state":{"opponent_defense_delta":0.2},
        "base_receiving_yards_per_reception":10.0,
        "shadow_receiving_yards_per_reception":10.1,
        "receiving_defense_state":{"opponent_defense_delta":0.1},
    }
    receipt=module.build_receipt(
        source=source,
        shadow=shadow,
        manifest={"manifest_sha256":"a"*64},
        player_audit={"P1":audit},
        frozen=frozen,
        recorded_utc=datetime(2026,9,20,19,0,tzinfo=timezone.utc),
        source_workflow_run="1",
        source_head_sha="b"*40,
        source_season=2026,
        source_week=2,
        v1_samples=np.array([40,50,60,70,80],dtype=float),
        shadow_samples=np.array([42,52,62,72,82],dtype=float),
    )
    assert receipt is None


def test_shadow_overlay_normalizes_opponent_alias():
    module=_module()
    player=SimpleNamespace(
        player_id="P1",
        opponent="JAC",
        rushing_yards_per_carry=4.3,
        rushing_yards_shape_per_carry=2.0,
        rushing_yards_per_carry_event_sd=3.0,
        rushing_yards_per_carry_mean_se=0.1,
        receiving_yards_per_reception=10.0,
        receiving_yards_shape_per_reception=2.0,
        receiving_yards_per_reception_event_sd=5.0,
        receiving_yards_per_reception_mean_se=0.1,
    )
    n=20
    stats={
        "active":np.ones(n,dtype=int),
        "pass_attempts":np.zeros(n,dtype=int),
        "routes":np.arange(n)%10,
        "targets":np.arange(n)%5,
        "receptions":np.arange(n)%4,
        "carries":np.arange(n)%6,
        "rushing_yards":np.zeros(n,dtype=int),
        "receiving_yards":np.zeros(n,dtype=int),
    }
    baseline=DummyResult(
        game_id="G-JAX",
        model_version="V1",
        players=(player,),
        player_stats={"P1":{k:v.copy() for k,v in stats.items()}},
    )
    frozen=module.load_frozen_coefficients(FROZEN)
    defense={
        "JAX":{
            "rushing":{"opponent_defense_delta":0.1},
            "receiving":{"opponent_defense_delta":0.2},
        }
    }
    shadow,audit=module.apply_shadow_a(
        baseline,defense_state=defense,frozen=frozen
    )
    assert shadow.model_version==module.SHADOW_VERSION
    assert audit["P1"]["opponent"]=="JAX"


def test_shadow_overlay_uses_retrospective_candidate_rng_namespace():
    module=_module()
    player=SimpleNamespace(
        player_id="P1",
        opponent="LAR",
        rushing_yards_per_carry=4.3,
        rushing_yards_shape_per_carry=2.0,
        rushing_yards_per_carry_event_sd=3.0,
        rushing_yards_per_carry_mean_se=0.1,
        receiving_yards_per_reception=10.0,
        receiving_yards_shape_per_reception=2.0,
        receiving_yards_per_reception_event_sd=5.0,
        receiving_yards_per_reception_mean_se=0.1,
    )
    n=40
    carries=np.arange(n)%9
    stats={
        "active":np.ones(n,dtype=int),
        "pass_attempts":np.zeros(n,dtype=int),
        "routes":np.arange(n)%12,
        "targets":np.arange(n)%7,
        "receptions":np.arange(n)%5,
        "carries":carries.copy(),
        "rushing_yards":np.zeros(n,dtype=int),
        "receiving_yards":np.zeros(n,dtype=int),
    }
    baseline=DummyResult(
        game_id="G-SEED",
        model_version="V1",
        players=(player,),
        player_stats={"P1":{k:v.copy() for k,v in stats.items()}},
    )
    frozen=module.load_frozen_coefficients(FROZEN)
    defense={
        "LAR":{
            "rushing":{"opponent_defense_delta":0.3},
            "receiving":{"opponent_defense_delta":0.5},
        }
    }
    shadow,_=module.apply_shadow_a(
        baseline,defense_state=defense,frozen=frozen
    )
    rush_mean=module.adjusted_mean(
        player.rushing_yards_per_carry,
        defense["LAR"]["rushing"]["opponent_defense_delta"],
        frozen["fits"]["rushing"],
    )
    rng=np.random.default_rng(module._stable_seed(
        module.RETROSPECTIVE_MECHANISM_VERSION,
        "rushing",
        baseline.game_id,
        player.player_id,
    ))
    expected=module._compound_yards(
        carries,
        rush_mean,
        player.rushing_yards_shape_per_carry,
        rng,
        event_sd=player.rushing_yards_per_carry_event_sd,
        mean_se=player.rushing_yards_per_carry_mean_se,
    )
    assert module.RETROSPECTIVE_MECHANISM_VERSION=="levline-props-v2-defensive-efficiency-pregame-v0.1.0"
    assert np.array_equal(shadow.player_stats["P1"]["rushing_yards"],expected)


def test_v1_replay_verification_is_strict():
    module=_module()
    source={
        "forecast_id":"fid",
        "market":{"line":60.5,"no_vig_over_probability":0.51},
        "model":{
            "version":"V1",
            "fair_line":62.0,
            "over_probability":0.54,
            "under_probability":0.46,
            "standard_deviation":20.0,
            "prediction_interval":{"low":30.0,"high":90.0,"coverage":0.80},
        },
    }
    replay=json.loads(json.dumps(source))
    module._assert_replay_matches_source(replay,source)

    drift=json.loads(json.dumps(source))
    drift["model"]["prediction_interval"]["high"]=90.01
    with pytest.raises(module.FootballShadowError,match="prediction_interval.high"):
        module._assert_replay_matches_source(drift,source)

    drift=json.loads(json.dumps(source))
    drift["market"]["line"]=61.5
    with pytest.raises(module.FootballShadowError,match="market.line"):
        module._assert_replay_matches_source(drift,source)


def test_empirical_distribution_snapshot_is_lossless():
    module=_module()
    snapshot=module._empirical_distribution_snapshot(
        np.array([1.0,1.0,2.0,4.0,4.0,4.0])
    )
    assert snapshot["sample_count"]==6
    assert snapshot["support"]==[1.0,2.0,4.0]
    assert snapshot["counts"]==[2,1,3]
    assert sum(snapshot["counts"])==snapshot["sample_count"]
    assert len(snapshot["sha256"])==64
