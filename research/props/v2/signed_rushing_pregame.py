from __future__ import annotations

"""Pregame signed-rushing overlay for LevLine Props 2.0 research.

This challenger keeps the frozen V1 opportunity simulation, including sampled carry counts, and
replaces only the conditional rushing-yard draw. Training residuals come from prior-season rushing
events. Target-game event counts and target-game yardage never enter the forecast.
"""

from dataclasses import dataclass, asdict
import hashlib
from typing import Any

import numpy as np
import pandas as pd

CONTRACT_VERSION = "levline-props-v2-signed-rushing-pregame-v0.1.0"
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
MIN_POOL_EVENTS = 250


class SignedRushingPregameError(ValueError):
    pass


@dataclass(frozen=True)
class ResidualPoolAudit:
    position: str
    trained_through_season: int
    n_events: int
    mean_yards: float
    negative_event_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_seed(*parts: Any) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)


def player_positions(players: pd.DataFrame) -> dict[str, str]:
    id_col = next((c for c in ("gsis_id", "player_id") if c in players.columns), None)
    pos_col = next((c for c in ("position", "position_group") if c in players.columns), None)
    if id_col is None or pos_col is None:
        raise SignedRushingPregameError("players table missing stable ID or position")
    work = players[[id_col, pos_col]].copy()
    work[id_col] = work[id_col].astype("string").fillna("").str.strip()
    work[pos_col] = work[pos_col].astype("string").fillna("").str.upper().str.strip()
    work = work[work[id_col].ne("") & work[pos_col].isin(SUPPORTED_POSITIONS)].copy()
    work = work.drop_duplicates(id_col, keep="last")
    return dict(zip(work[id_col].astype(str), work[pos_col].astype(str)))


def build_rushing_event_rows(
    pbp: pd.DataFrame,
    positions: dict[str, str],
) -> pd.DataFrame:
    required = {"game_id", "season", "week"}
    missing = required - set(pbp.columns)
    if missing:
        raise SignedRushingPregameError(f"PBP missing fields: {sorted(missing)}")
    work = pbp.copy()
    if "season_type" in work.columns:
        work = work[work["season_type"].astype(str).str.upper().eq("REG")].copy()
    elif "game_type" in work.columns:
        work = work[work["game_type"].astype(str).str.upper().eq("REG")].copy()

    rusher_col = next((c for c in ("rusher_player_id", "rusher_id") if c in work.columns), None)
    yard_col = next((c for c in ("rushing_yards", "yards_gained") if c in work.columns), None)
    if rusher_col is None or yard_col is None:
        raise SignedRushingPregameError("PBP missing stable rusher ID or rushing yardage")

    rush = pd.to_numeric(work.get("rush_attempt", 0), errors="coerce").fillna(0).eq(1)
    rusher = work[rusher_col].astype("string").fillna("").str.strip()
    yards = pd.to_numeric(work[yard_col], errors="coerce")
    mask = rush & rusher.ne("") & yards.notna()
    frame = work.loc[mask, ["game_id", "season", "week"]].copy()
    frame["player_id"] = rusher.loc[mask].astype(str).to_numpy()
    frame["yards"] = yards.loc[mask].astype(float).to_numpy()
    frame["position"] = frame["player_id"].map(positions).astype("string").fillna("").str.upper()
    frame = frame[frame["position"].isin(SUPPORTED_POSITIONS)].copy()
    frame["season"] = pd.to_numeric(frame["season"], errors="coerce").astype(int)
    frame["week"] = pd.to_numeric(frame["week"], errors="coerce").astype(int)
    return frame.reset_index(drop=True)


def fit_residual_pools(
    events: pd.DataFrame,
    *,
    trained_through_season: int,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if int(trained_through_season) > 2025:
        raise SignedRushingPregameError("completed 2026 outcomes are prohibited")
    train = events[events["season"].astype(int).le(int(trained_through_season))].copy()
    if train.empty:
        raise SignedRushingPregameError("empty rushing-event training set")

    pools: dict[str, np.ndarray] = {}
    audits: dict[str, Any] = {}
    pooled = pd.to_numeric(train["yards"], errors="coerce").dropna().to_numpy(dtype=float)
    if len(pooled) < MIN_POOL_EVENTS:
        raise SignedRushingPregameError("insufficient pooled rushing events")
    pooled_residuals = pooled - float(np.mean(pooled))

    for position in sorted(SUPPORTED_POSITIONS):
        vals = pd.to_numeric(
            train.loc[train["position"].eq(position), "yards"], errors="coerce"
        ).dropna().to_numpy(dtype=float)
        if len(vals) >= MIN_POOL_EVENTS:
            residuals = vals - float(np.mean(vals))
            scope = "position"
            source = vals
        else:
            residuals = pooled_residuals
            scope = "pooled_position_fallback"
            source = pooled
        pools[position] = residuals.astype(float)
        audits[position] = {
            **ResidualPoolAudit(
                position=position,
                trained_through_season=int(trained_through_season),
                n_events=int(len(source)),
                mean_yards=float(np.mean(source)),
                negative_event_rate=float(np.mean(source < 0.0)),
            ).to_dict(),
            "scope": scope,
        }
    return pools, {
        "contract_version": CONTRACT_VERSION,
        "trained_through_season": int(trained_through_season),
        "positions": audits,
        "target_game_events_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def signed_rushing_samples(
    carries: np.ndarray,
    *,
    mean_per_carry: float,
    mean_se: float,
    residual_pool: np.ndarray,
    seed: int,
) -> np.ndarray:
    counts = np.asarray(carries, dtype=np.int64)
    residuals = np.asarray(residual_pool, dtype=float)
    residuals = residuals[np.isfinite(residuals)]
    if residuals.size < 2:
        raise SignedRushingPregameError("signed rushing residual pool requires >=2 events")
    if np.any(counts < 0):
        raise SignedRushingPregameError("carry counts must be nonnegative")

    rng = np.random.default_rng(int(seed))
    mean = float(mean_per_carry)
    se = max(float(mean_se), 0.0)
    latent = (
        np.maximum(rng.normal(mean, se, size=len(counts)), 0.0)
        if se > 0.0
        else np.full(len(counts), max(mean, 0.0), dtype=float)
    )
    out = np.zeros(len(counts), dtype=float)
    for count in np.unique(counts):
        count = int(count)
        if count <= 0:
            continue
        indexes = np.flatnonzero(counts == count)
        draws = rng.choice(residuals, size=(len(indexes), count), replace=True)
        out[indexes] = latent[indexes] * count + draws.sum(axis=1)
    return np.rint(out).astype(np.int64)


def apply_signed_rushing_overlay(
    simulation,
    game_input,
    residual_pools: dict[str, np.ndarray],
    *,
    seed_namespace: str,
):
    """Mutate only research-result rushing-yard arrays and return an audit.

    The simulation object is expected to be a fresh research result. Carry arrays are preserved
    byte-for-byte.
    """
    players = {p.player_id: p for p in game_input.players}
    audit = {
        "contract_version": CONTRACT_VERSION,
        "players_overlaid": 0,
        "players_missing_pool": 0,
        "carry_arrays_modified": 0,
        "target_game_carries_used_for_fit": 0,
        "target_game_yards_used_for_fit": 0,
    }
    for player_id, stats in simulation.player_stats.items():
        player = players.get(player_id)
        if player is None:
            continue
        position = str(player.position).upper()
        pool = residual_pools.get(position)
        if pool is None:
            audit["players_missing_pool"] += 1
            continue
        original_carries = np.asarray(stats["carries"]).copy()
        signed = signed_rushing_samples(
            original_carries,
            mean_per_carry=float(player.rushing_yards_per_carry),
            mean_se=float(player.rushing_yards_per_carry_mean_se),
            residual_pool=pool,
            seed=_stable_seed(CONTRACT_VERSION, seed_namespace, player_id),
        )
        stats["rushing_yards"] = signed
        if not np.array_equal(original_carries, np.asarray(stats["carries"])):
            audit["carry_arrays_modified"] += 1
        audit["players_overlaid"] += 1
    return audit


def empirical_crps(samples: np.ndarray, observation: float) -> float:
    values = np.asarray(samples, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise SignedRushingPregameError("CRPS requires finite samples")
    ordered = np.sort(values)
    n = ordered.size
    first = float(np.mean(np.abs(ordered - float(observation))))
    weights = 2.0 * np.arange(n, dtype=float) - float(n) + 1.0
    half_pairwise = float(np.dot(weights, ordered) / float(n * n))
    return float(max(0.0, first - half_pairwise))
