from __future__ import annotations

"""Naive weekly F-ST refit negative control.

For every target week, refit the same two-input market/PURE logistic stack using every
chronologically available prior row, including completed weeks from the current season.
This directly tests the simple hypothesis "retrain F-ST every week" while preventing
same-week leakage.

Research-only negative control. No 2026 outcomes and no production mutation.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from nfl_forecast.challenger_stacking import build_chronological_logit_stack

SOURCE = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
TARGET_SEASONS = (2022, 2023, 2024, 2025)
EPS = 1e-6
CANDIDATE_ID = "NAIVE-WEEKLY-FST-REFIT-CONTROL-V1"


def _logit(values) -> np.ndarray:
    p = np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def _parse_game_id(game_id: str) -> tuple[int, int]:
    parts = str(game_id).split("_")
    if len(parts) != 4:
        raise ValueError(f"unexpected game id: {game_id}")
    return int(parts[0]), int(parts[1])


def load_frame(path: str | Path = SOURCE) -> pd.DataFrame:
    source = pd.read_csv(path).copy()
    parsed = source["game_id"].astype(str).map(_parse_game_id)
    source["season_num"] = [x[0] for x in parsed]
    source["week"] = [x[1] for x in parsed]
    source["home_win_num"] = pd.to_numeric(source["home_win"], errors="coerce")
    source["market_prob_num"] = pd.to_numeric(source["market_prob"], errors="coerce")
    source["pure_prob_num"] = pd.to_numeric(source["pure_prob"], errors="coerce")
    source = source[
        source["home_win_num"].isin([0, 1])
        & source["market_prob_num"].between(EPS, 1 - EPS)
        & source["pure_prob_num"].between(EPS, 1 - EPS)
    ].copy()
    return source.sort_values(["season_num", "week", "game_id"], kind="stable")


def weekly_refit_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    target = frame[frame["season_num"].isin(TARGET_SEASONS)].copy()

    for (season, week), current in target.groupby(["season_num", "week"], sort=True):
        prior = (
            (frame["season_num"] < int(season))
            | ((frame["season_num"] == int(season)) & (frame["week"] < int(week)))
        )
        train = frame.loc[prior].copy()
        if len(train) < 300:
            raise RuntimeError(f"insufficient prior rows for {season} W{week}: {len(train)}")

        x_train = np.column_stack([
            _logit(train["market_prob_num"]),
            _logit(train["pure_prob_num"]),
        ])
        x_current = np.column_stack([
            _logit(current["market_prob_num"]),
            _logit(current["pure_prob_num"]),
        ])
        model = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=3000)
        model.fit(x_train, train["home_win_num"].astype(int))
        probability = model.predict_proba(x_current)[:, 1]

        part = current[[
            "game_id", "season_num", "week", "home_win_num", "market_prob_num", "pure_prob_num"
        ]].copy()
        part = part.rename(columns={"season_num":"season", "home_win_num":"home_win"})
        part["weekly_refit_prob"] = probability
        part["training_games"] = int(len(train))
        part["training_last_season"] = int(train["season_num"].max())
        part["training_last_week"] = int(
            train.loc[train["season_num"].eq(train["season_num"].max()), "week"].max()
        )
        part["same_week_outcomes_used"] = False
        rows.append(part)

    return pd.concat(rows, ignore_index=True)


def attach_frozen_fst(frame: pd.DataFrame, path: str | Path = SOURCE) -> pd.DataFrame:
    source = pd.read_csv(path)
    stack = build_chronological_logit_stack(source, target_seasons=TARGET_SEASONS)
    fst = stack.predictions.copy()
    fst["game_id"] = source.loc[fst.index, "game_id"].astype(str)
    fst = fst[["game_id", "stack_probability"]].rename(columns={"stack_probability":"fst_prob"})
    return frame.merge(fst, on="game_id", how="inner", validate="one_to_one")


def evaluate(scored: pd.DataFrame) -> dict:
    y = scored["home_win"].astype(int)
    fst_correct = scored["fst_prob"].ge(0.5).astype(int).eq(y)
    weekly_correct = scored["weekly_refit_prob"].ge(0.5).astype(int).eq(y)
    switch = scored["fst_prob"].ge(0.5).ne(scored["weekly_refit_prob"].ge(0.5))
    weekly_only = int((switch & weekly_correct & ~fst_correct).sum())
    fst_only = int((switch & fst_correct & ~weekly_correct).sum())

    return {
        "candidate_id": CANDIDATE_ID,
        "status": "negative_control",
        "games": int(len(scored)),
        "fst_correct": int(fst_correct.sum()),
        "fst_accuracy": float(fst_correct.mean()),
        "weekly_refit_correct": int(weekly_correct.sum()),
        "weekly_refit_accuracy": float(weekly_correct.mean()),
        "accuracy_delta_pp": float(100.0 * (weekly_correct.mean() - fst_correct.mean())),
        "switches": int(switch.sum()),
        "weekly_refit_only_correct": weekly_only,
        "fst_only_correct": fst_only,
        "switch_win_rate": float(weekly_only / switch.sum()) if switch.sum() else None,
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
        "promotion_authorized": False,
    }


def run(output_dir: str = "research_outputs/naive_weekly_fst_refit_control_v1") -> dict:
    base = load_frame()
    weekly = weekly_refit_predictions(base)
    scored = attach_frozen_fst(weekly)
    report = evaluate(scored)
    if report["fst_correct"] != 741:
        raise RuntimeError(f"incumbent reproduction drift: {report['fst_correct']} != 741")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out / "scored_games.csv", index=False)
    (out / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/naive_weekly_fst_refit_control_v1")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
