from __future__ import annotations

"""Bayesian-shrinkage residual team-state challenger for weekly LevLine learning.

The incumbent chronology-clean F-ST probability is the prior forecast.  This module
learns only persistent team-level residual state around that forecast.  All games in
a week are scored from preweek state and outcomes are batch-applied afterward, so no
same-week result can affect another game.

Research-only: no 2026 outcomes and no production mutation.
"""

from collections import defaultdict
from dataclasses import dataclass
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_stacking import build_chronological_logit_stack

SOURCE = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
TARGET_SEASONS = (2022, 2023, 2024, 2025)
EPS = 1e-6
CANDIDATE_ID = "ADAPTIVE-RESIDUAL-STATE-V1"


@dataclass(frozen=True)
class StateConfig:
    initial_variance: float = 0.20
    process_variance_per_week: float = 0.03
    weekly_mean_reversion: float = 0.97
    offseason_mean_reversion: float = 0.50
    max_abs_state_logit: float = 1.00


DEFAULT_CONFIG = StateConfig()


def _logit(p: np.ndarray | pd.Series) -> np.ndarray:
    x = np.clip(np.asarray(p, dtype=float), EPS, 1.0 - EPS)
    return np.log(x / (1.0 - x))


def _sigmoid(x: np.ndarray | float) -> np.ndarray:
    z = np.asarray(x, dtype=float)
    return 1.0 / (1.0 + np.exp(-z))


def _parse_game_id(game_id: str) -> tuple[int, int, str, str]:
    parts = str(game_id).split("_")
    if len(parts) != 4:
        raise ValueError(f"unexpected game_id: {game_id}")
    season, week, away, home = parts
    return int(season), int(week), away, home


def load_fst_replay(path: str | Path = SOURCE) -> pd.DataFrame:
    source = pd.read_csv(path)
    stack = build_chronological_logit_stack(source, target_seasons=TARGET_SEASONS)
    pred = stack.predictions.copy()
    pred["game_id"] = source.loc[pred.index, "game_id"].astype(str)
    parsed = pred["game_id"].map(_parse_game_id)
    pred["season"] = [x[0] for x in parsed]
    pred["week"] = [x[1] for x in parsed]
    pred["away_team"] = [x[2] for x in parsed]
    pred["home_team"] = [x[3] for x in parsed]
    pred["home_win"] = pd.to_numeric(pred["home_win"], errors="raise").astype(int)
    pred["fst_prob"] = pd.to_numeric(pred["stack_probability"], errors="raise")
    return pred.sort_values(["season", "week", "game_id"], kind="stable").reset_index(drop=True)


def run_state_filter(frame: pd.DataFrame, config: StateConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    required = {"game_id", "season", "week", "home_team", "away_team", "home_win", "fst_prob"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"adaptive residual frame missing fields: {sorted(missing)}")

    mean: dict[str, float] = defaultdict(float)
    variance: dict[str, float] = defaultdict(lambda: float(config.initial_variance))
    rows: list[dict] = []
    previous_season: int | None = None

    for (season, week), group in frame.groupby(["season", "week"], sort=True):
        season = int(season)
        week = int(week)

        if previous_season is not None and season != previous_season:
            for team in list(mean):
                mean[team] *= config.offseason_mean_reversion
                variance[team] = max(variance[team], config.initial_variance)
        previous_season = season

        # State evolution happens before observing this week.
        teams = set(group["home_team"].astype(str)) | set(group["away_team"].astype(str))
        for team in teams:
            mean[team] *= config.weekly_mean_reversion
            variance[team] += config.process_variance_per_week

        gradients: dict[str, float] = defaultdict(float)
        information: dict[str, float] = defaultdict(float)

        # Forecast every game from the exact same preweek state.
        for record in group.sort_values("game_id").to_dict("records"):
            home = str(record["home_team"])
            away = str(record["away_team"])
            base = float(record["fst_prob"])
            if not (0.0 < base < 1.0):
                raise ValueError(f"invalid F-ST probability for {record['game_id']}")
            correction = mean[home] - mean[away]
            adaptive = float(_sigmoid(_logit([base])[0] + correction))
            y = int(record["home_win"])
            error = float(y - adaptive)
            fisher = float(adaptive * (1.0 - adaptive))

            rows.append({
                **record,
                "candidate_id": CANDIDATE_ID,
                "adaptive_prob": adaptive,
                "adaptive_logit_correction": correction,
                "home_state_preweek": float(mean[home]),
                "away_state_preweek": float(mean[away]),
                "home_variance_preweek": float(variance[home]),
                "away_variance_preweek": float(variance[away]),
                "forecast_error": error,
                "state_updates_use_same_week_outcomes": False,
            })

            # Accumulate; do not update until all forecasts in the week are frozen.
            gradients[home] += error
            gradients[away] -= error
            information[home] += fisher
            information[away] += fisher

        # Diagonal Laplace / extended-logistic update around preweek state.
        for team in teams:
            prior_var = max(float(variance[team]), 1e-9)
            post_var = 1.0 / (1.0 / prior_var + float(information[team]))
            post_mean = float(mean[team] + post_var * gradients[team])
            mean[team] = float(np.clip(
                post_mean,
                -config.max_abs_state_logit,
                config.max_abs_state_logit,
            ))
            variance[team] = float(post_var)

    return pd.DataFrame(rows)


def _log_loss(p: pd.Series, y: pd.Series) -> float:
    prob = np.clip(pd.to_numeric(p, errors="raise").to_numpy(float), EPS, 1.0 - EPS)
    target = pd.to_numeric(y, errors="raise").to_numpy(float)
    return float(np.mean(-(target * np.log(prob) + (1 - target) * np.log(1 - prob))))


def evaluate(scored: pd.DataFrame, config: StateConfig = DEFAULT_CONFIG) -> dict:
    y = scored["home_win"].astype(int)
    scored = scored.copy()
    scored["fst_correct"] = (scored["fst_prob"].ge(0.5).astype(int) == y).astype(int)
    scored["adaptive_correct"] = (scored["adaptive_prob"].ge(0.5).astype(int) == y).astype(int)
    scored["switch"] = scored["fst_prob"].ge(0.5) != scored["adaptive_prob"].ge(0.5)
    switched = scored[scored["switch"]]
    adaptive_only = int((switched["adaptive_correct"].eq(1) & switched["fst_correct"].eq(0)).sum())
    fst_only = int((switched["fst_correct"].eq(1) & switched["adaptive_correct"].eq(0)).sum())

    by_season = []
    for season, part in scored.groupby("season", sort=True):
        by_season.append({
            "season": int(season),
            "games": int(len(part)),
            "fst_correct": int(part["fst_correct"].sum()),
            "adaptive_correct": int(part["adaptive_correct"].sum()),
            "accuracy_delta_pp": float(
                100.0 * (part["adaptive_correct"].mean() - part["fst_correct"].mean())
            ),
            "switches": int(part["switch"].sum()),
        })

    return {
        "candidate_id": CANDIDATE_ID,
        "status": "historical_fixed_candidate_not_promotion_proof",
        "governance": {
            "same_week_updates_allowed": False,
            "completed_2026_outcomes_used": 0,
            "production_changed": False,
            "promotion_authorized": False,
        },
        "algorithm": {
            **config.__dict__,
            "update": "diagonal Laplace/extended-logistic residual state around F-ST",
            "prior_center": "zero residual correction to F-ST",
        },
        "sample": {"games": int(len(scored)), "seasons": sorted(scored["season"].astype(int).unique().tolist())},
        "results": {
            "fst_correct": int(scored["fst_correct"].sum()),
            "fst_accuracy": float(scored["fst_correct"].mean()),
            "adaptive_correct": int(scored["adaptive_correct"].sum()),
            "adaptive_accuracy": float(scored["adaptive_correct"].mean()),
            "accuracy_delta_pp": float(
                100.0 * (scored["adaptive_correct"].mean() - scored["fst_correct"].mean())
            ),
            "fst_brier": float(np.mean((scored["fst_prob"] - y) ** 2)),
            "adaptive_brier": float(np.mean((scored["adaptive_prob"] - y) ** 2)),
            "fst_log_loss": _log_loss(scored["fst_prob"], y),
            "adaptive_log_loss": _log_loss(scored["adaptive_prob"], y),
            "switches": int(len(switched)),
            "adaptive_only_correct": adaptive_only,
            "fst_only_correct": fst_only,
            "switch_win_rate": float(adaptive_only / len(switched)) if len(switched) else None,
        },
        "by_season": by_season,
    }


def run(output_dir: str = "research_outputs/adaptive_residual_state_v1") -> dict:
    base = load_fst_replay()
    scored = run_state_filter(base)
    report = evaluate(scored)
    if report["results"]["fst_correct"] != 741:
        raise RuntimeError(f"incumbent reproduction drift: {report['results']['fst_correct']} != 741")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out / "scored_games.csv", index=False)
    (out / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/adaptive_residual_state_v1")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
