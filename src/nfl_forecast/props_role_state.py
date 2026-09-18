from __future__ import annotations

"""Strictly lagged player-role state for LevLine Props challengers.

The first deployable role signal uses offensive snap share, because it is available
game-by-game and can be reproduced prospectively. Historical participation/route charting
may be richer but is not assumed to be a live in-season source.

This module intentionally produces conservative multipliers around 1.0. It is not a
standalone projection model and never reads target-game participation.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping

import numpy as np
import pandas as pd

ENGINE_VERSION = "levline-props-snap-role-state-v0.1.0"
SUPPORTED_POSITIONS = frozenset({"RB", "WR", "TE"})
DEFAULT_RECENT_HALF_LIFE_GAMES = 2.0
DEFAULT_BASELINE_HALF_LIFE_GAMES = 8.0
DEFAULT_LOG_RATIO_SHRINKAGE = 0.50
DEFAULT_MULTIPLIER_FLOOR = 2.0 / 3.0
DEFAULT_MULTIPLIER_CAP = 1.50
DEFAULT_MIN_OBSERVATIONS = 2
MIN_BASELINE_SHARE = 0.05


class RoleStateError(ValueError):
    """Raised when snap-role state cannot be constructed safely."""


@dataclass(frozen=True)
class SnapRoleConfig:
    recent_half_life_games: float = DEFAULT_RECENT_HALF_LIFE_GAMES
    baseline_half_life_games: float = DEFAULT_BASELINE_HALF_LIFE_GAMES
    log_ratio_shrinkage: float = DEFAULT_LOG_RATIO_SHRINKAGE
    multiplier_floor: float = DEFAULT_MULTIPLIER_FLOOR
    multiplier_cap: float = DEFAULT_MULTIPLIER_CAP
    min_observations: int = DEFAULT_MIN_OBSERVATIONS

    def validate(self) -> None:
        if self.recent_half_life_games <= 0 or self.baseline_half_life_games <= 0:
            raise RoleStateError("half lives must be positive")
        if self.recent_half_life_games >= self.baseline_half_life_games:
            raise RoleStateError("recent half life must be shorter than baseline half life")
        if not (0.0 < self.log_ratio_shrinkage <= 1.0):
            raise RoleStateError("log_ratio_shrinkage must lie in (0, 1]")
        if not (0.0 < self.multiplier_floor <= 1.0 <= self.multiplier_cap):
            raise RoleStateError("multiplier bounds must straddle 1.0")
        if self.min_observations < 1:
            raise RoleStateError("min_observations must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _team(value: Any) -> str:
    text = str(value or "").upper().strip()
    aliases = {"JAC": "JAX", "LA": "LAR", "STL": "LAR", "WSH": "WAS"}
    return aliases.get(text, text)


def _snap_share(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    # PFR/nflverse offense_pct can be represented either as a fraction or a percentage.
    finite = values[np.isfinite(values)]
    if not finite.empty and float(finite.quantile(0.95)) > 1.5:
        values = values / 100.0
    return values.clip(lower=0.0, upper=1.0)


def _ewm_mean(values: np.ndarray, half_life_games: float) -> float:
    if len(values) == 0:
        raise RoleStateError("cannot compute EWM over an empty sequence")
    ages = np.arange(len(values) - 1, -1, -1, dtype=float)
    weights = np.power(0.5, ages / float(half_life_games))
    return float(np.average(values, weights=weights))


def _validate_snap_history(snap_counts: pd.DataFrame) -> pd.DataFrame:
    required = {"season", "week", "team", "player_id", "offense_pct"}
    missing = required - set(snap_counts.columns)
    if missing:
        raise RoleStateError(f"snap counts missing fields: {sorted(missing)}")
    out = snap_counts.copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce")
    out["week"] = pd.to_numeric(out["week"], errors="coerce")
    out["player_id"] = out["player_id"].astype("string").fillna("").str.strip()
    out["team"] = out["team"].map(_team)
    out["offense_share"] = _snap_share(out["offense_pct"])
    out = out[
        out["season"].notna()
        & out["week"].notna()
        & out["player_id"].ne("")
        & out["player_id"].ne("<NA>")
        & out["offense_share"].notna()
    ].copy()
    out["season"] = out["season"].astype(int)
    out["week"] = out["week"].astype(int)
    if "game_type" in out.columns:
        out = out[out["game_type"].astype(str).str.upper().eq("REG")].copy()
    return out


def build_snap_trend_role_adjustments(
    snap_counts: pd.DataFrame,
    current_players: pd.DataFrame,
    *,
    season: int,
    week: int,
    team: str,
    config: SnapRoleConfig | None = None,
) -> tuple[dict[str, dict[str, float]], dict[str, Any]]:
    """Build strictly lagged general-role multipliers for current RB/WR/TE players.

    The multiplier is a shrunk ratio of short-horizon to long-horizon offensive snap
    share. Both means are estimated from the same player's completed games for the
    current team, so the signal is a *trend* rather than a second copy of absolute usage.

    Rows from the target week or any future period are rejected from the eligible history.
    Missing/insufficient evidence yields a neutral 1.0 multiplier.
    """

    cfg = config or SnapRoleConfig()
    cfg.validate()
    history = _validate_snap_history(snap_counts)
    team_norm = _team(team)

    unsafe = (history["season"] > int(season)) | (
        history["season"].eq(int(season)) & history["week"].ge(int(week))
    )
    eligible_history = history.loc[~unsafe & history["team"].eq(team_norm)].copy()
    eligible_history = eligible_history.sort_values(
        ["season", "week"] + (["game_id"] if "game_id" in eligible_history.columns else [])
    )

    required_players = {"player_id", "position", "team"}
    missing = required_players - set(current_players.columns)
    if missing:
        raise RoleStateError(f"current players missing fields: {sorted(missing)}")

    current = current_players.copy()
    current["player_id"] = current["player_id"].astype("string").fillna("").str.strip()
    current["position"] = current["position"].astype(str).str.upper().str.strip()
    current["team"] = current["team"].map(_team)
    current = current[
        current["team"].eq(team_norm)
        & current["position"].isin(SUPPORTED_POSITIONS)
        & current["player_id"].ne("")
    ].copy()

    adjustments: dict[str, dict[str, float]] = {}
    players_audit: dict[str, Any] = {}

    for _, player in current.iterrows():
        pid = str(player["player_id"])
        rows = eligible_history[eligible_history["player_id"].eq(pid)].copy()
        values = rows["offense_share"].to_numpy(dtype=float)
        audit = {
            "position": str(player["position"]),
            "observations": int(len(values)),
            "multiplier": 1.0,
            "reason": "neutral_insufficient_history",
        }
        if len(values) >= cfg.min_observations:
            recent = _ewm_mean(values, cfg.recent_half_life_games)
            baseline = _ewm_mean(values, cfg.baseline_half_life_games)
            audit.update({"recent_snap_share": recent, "baseline_snap_share": baseline})
            if baseline >= MIN_BASELINE_SHARE and recent > 0.0:
                raw_ratio = recent / baseline
                shrunk_ratio = math.exp(
                    cfg.log_ratio_shrinkage * math.log(max(raw_ratio, 1e-6))
                )
                multiplier = float(
                    min(cfg.multiplier_cap, max(cfg.multiplier_floor, shrunk_ratio))
                )
                audit.update(
                    {
                        "raw_recent_to_baseline_ratio": raw_ratio,
                        "multiplier": multiplier,
                        "reason": "strictly_lagged_snap_trend",
                    }
                )
                if not math.isclose(multiplier, 1.0, abs_tol=1e-12):
                    adjustments[pid] = {"role_multiplier": multiplier}
            else:
                audit["reason"] = "neutral_low_baseline_share"
        players_audit[pid] = audit

    max_period = None
    if not eligible_history.empty:
        latest = eligible_history.sort_values(["season", "week"]).iloc[-1]
        max_period = {"season": int(latest["season"]), "week": int(latest["week"])}

    return adjustments, {
        "engine_version": ENGINE_VERSION,
        "team": team_norm,
        "target_season": int(season),
        "target_week": int(week),
        "history_policy": "STRICT_PRIOR_WEEK",
        "historical_max_period_used": max_period,
        "target_or_future_rows_used": 0,
        "config": cfg.to_dict(),
        "adjusted_players": int(len(adjustments)),
        "eligible_current_players": int(len(current)),
        "players": players_audit,
    }
