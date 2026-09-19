from __future__ import annotations

"""True-pregame opponent defensive-efficiency overlay for Props 2.0 research."""

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Mapping

import numpy as np
import pandas as pd

from nfl_forecast.challenger_props_simulation import _compound_yards

CONTRACT_VERSION = "levline-props-v2-defensive-efficiency-pregame-v0.1.0"
SUPPORTED_MODES = ("rushing", "receiving")
MIN_ADJUSTED_MEAN = 0.05


class PregameDefensiveEfficiencyError(ValueError):
    pass


def _stable_seed(*parts: Any) -> int:
    digest=hashlib.sha256("|".join(map(str,parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8],"big") % (2**32-1)


def build_defense_delta_lookup(component_rows: pd.DataFrame) -> dict[tuple[str,str,str],float]:
    required={"game_id","defteam","event_type","opponent_defense_delta","same_week_outcomes_used"}
    missing=required-set(component_rows.columns)
    if missing:
        raise PregameDefensiveEfficiencyError(f"component rows missing fields: {sorted(missing)}")
    if not pd.to_numeric(component_rows["same_week_outcomes_used"],errors="coerce").fillna(1).eq(0).all():
        raise PregameDefensiveEfficiencyError("defense-state source is not strict prior-week")

    lookup={}
    for key,group in component_rows.groupby(["game_id","defteam","event_type"],sort=False):
        vals=pd.to_numeric(group["opponent_defense_delta"],errors="coerce").dropna().to_numpy(dtype=float)
        if len(vals)==0:
            continue
        if float(np.max(vals)-np.min(vals))>1e-10:
            raise PregameDefensiveEfficiencyError(f"inconsistent defense delta within game: {key}")
        lookup[(str(key[0]),str(key[1]),str(key[2]))]=float(vals[0])
    return lookup


def adjusted_mean(base_mean: float, defense_delta: float, fit: Mapping[str,Any]) -> float:
    x_sd=max(float(fit["x_sd"]),1e-9)
    z=(float(defense_delta)-float(fit["x_mean"]))/x_sd
    correction=float(fit["intercept"])+float(fit["beta_standardized"])*z
    return float(max(MIN_ADJUSTED_MEAN,float(base_mean)+correction))


def apply_defensive_efficiency_overlay(
    simulation,
    game_input,
    *,
    game_id: str,
    mode: str,
    fit: Mapping[str,Any],
    defense_delta_lookup: Mapping[tuple[str,str,str],float],
):
    mode=str(mode).strip().lower()
    if mode not in SUPPORTED_MODES:
        raise PregameDefensiveEfficiencyError(f"unsupported mode: {mode}")

    players={p.player_id:p for p in game_input.players}
    audit={
        "contract_version":CONTRACT_VERSION,
        "mode":mode,
        "players_adjusted":0,
        "players_missing_defense_state":0,
        "opportunity_arrays_modified":0,
        "target_game_events_used_for_fit":0,
        "target_game_yards_used_for_fit":0,
    }

    for player_id,stats in simulation.player_stats.items():
        player=players.get(player_id)
        if player is None:
            continue
        key=(str(game_id),str(player.opponent),mode)
        defense_delta=defense_delta_lookup.get(key)
        if defense_delta is None:
            audit["players_missing_defense_state"]+=1
            continue

        if mode=="rushing":
            count_key="carries"
            yard_key="rushing_yards"
            base_mean=float(player.rushing_yards_per_carry)
            shape=float(player.rushing_yards_shape_per_carry)
            event_sd=player.rushing_yards_per_carry_event_sd
            mean_se=float(player.rushing_yards_per_carry_mean_se)
        else:
            count_key="receptions"
            yard_key="receiving_yards"
            base_mean=float(player.receiving_yards_per_reception)
            shape=float(player.receiving_yards_shape_per_reception)
            event_sd=player.receiving_yards_per_reception_event_sd
            mean_se=float(player.receiving_yards_per_reception_mean_se)

        counts=np.asarray(stats[count_key]).copy()
        mean=adjusted_mean(base_mean,float(defense_delta),fit)
        rng=np.random.default_rng(_stable_seed(CONTRACT_VERSION,mode,game_id,player_id))
        stats[yard_key]=_compound_yards(
            counts,
            mean,
            shape,
            rng,
            event_sd=event_sd,
            mean_se=mean_se,
        )
        if not np.array_equal(counts,np.asarray(stats[count_key])):
            audit["opportunity_arrays_modified"]+=1
        audit["players_adjusted"]+=1

    return audit
