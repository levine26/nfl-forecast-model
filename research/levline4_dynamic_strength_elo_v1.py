from __future__ import annotations

"""Research-only fixed Elo / dynamic-strength residual audit for LevLine 4.

The purpose is not to optimize an Elo model. It asks whether a simple sequential team-strength
state adds winner-accuracy information once the chronology-clean F-ST inputs are already
present. All games in a week are scored from ratings frozen at the start of that week; outcomes
from the week are batch-applied only after every probability for that week is recorded.

No 2026 outcomes are used and no production surface is modified.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

BASE_OOF = Path("challenger_outputs/fst/provenance/base_oof_keyed.csv")
TRAINING_KEYED = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
TARGET_SEASONS = (2022, 2023, 2024, 2025)
ELO_K = 20.0
ELO_HOME_ADVANTAGE = 55.0
OFFSEASON_REGRESSION = 1.0 / 3.0
ELO_MEAN = 1500.0
EPS = 1e-6


def _parse_game_id(game_id: str) -> tuple[int, int, str, str]:
    parts = str(game_id).split("_")
    if len(parts) != 4:
        raise ValueError(f"unexpected game_id: {game_id}")
    season, week, away, home = parts
    return int(season), int(week), away, home


def _elo_prob(home_rating: float, away_rating: float) -> float:
    diff = home_rating + ELO_HOME_ADVANTAGE - away_rating
    return float(1.0 / (1.0 + 10.0 ** (-diff / 400.0)))


def _load() -> pd.DataFrame:
    base = pd.read_csv(BASE_OOF)
    keyed = pd.read_csv(TRAINING_KEYED)
    frame = base[["game_id", "home_win", "season"]].merge(
        keyed[["game_id", "market_prob", "pure_prob", "home_win", "season"]],
        on="game_id",
        suffixes=("_base", "_keyed"),
        how="inner",
        validate="one_to_one",
    )
    if not (frame["home_win_base"].astype(int) == frame["home_win_keyed"].astype(int)).all():
        raise ValueError("outcome mismatch across provenance files")
    parsed = frame["game_id"].map(_parse_game_id)
    frame["season"] = [item[0] for item in parsed]
    frame["week"] = [item[1] for item in parsed]
    frame["away_team"] = [item[2] for item in parsed]
    frame["home_team"] = [item[3] for item in parsed]
    frame["home_win"] = frame["home_win_base"].astype(int)
    return frame.sort_values(["season", "week", "game_id"]).reset_index(drop=True)


def build_week_frozen_elo(frame: pd.DataFrame) -> pd.DataFrame:
    ratings: dict[str, float] = defaultdict(lambda: ELO_MEAN)
    rows: list[dict] = []
    prior_season: int | None = None

    for (season, week), group in frame.groupby(["season", "week"], sort=True):
        season = int(season)
        week = int(week)
        if prior_season != season:
            if prior_season is not None:
                for team in list(ratings):
                    ratings[team] = ELO_MEAN + (ratings[team] - ELO_MEAN) * (1.0 - OFFSEASON_REGRESSION)
            prior_season = season

        pending: list[tuple[str, str, float]] = []
        for record in group.sort_values("game_id").to_dict("records"):
            home = str(record["home_team"])
            away = str(record["away_team"])
            p = _elo_prob(ratings[home], ratings[away])
            rows.append({
                "game_id": record["game_id"],
                "season": season,
                "week": week,
                "home_win": int(record["home_win"]),
                "market_prob": float(record["market_prob"]),
                "pure_prob": float(record["pure_prob"]),
                "elo_home_prob": p,
                "home_elo_preweek": float(ratings[home]),
                "away_elo_preweek": float(ratings[away]),
            })
            pending.append((home, away, float(record["home_win"])))

        # Batch update: no game in this week can affect another game's pregame state.
        deltas: dict[str, float] = defaultdict(float)
        for home, away, outcome in pending:
            expected = _elo_prob(ratings[home], ratings[away])
            change = ELO_K * (outcome - expected)
            deltas[home] += change
            deltas[away] -= change
        for team, delta in deltas.items():
            ratings[team] += delta

    return pd.DataFrame(rows)


def _logit(values: pd.Series) -> np.ndarray:
    arr = np.clip(values.to_numpy(dtype=float), EPS, 1.0 - EPS)
    return np.log(arr / (1.0 - arr))


def _stack_predict(train: pd.DataFrame, test: pd.DataFrame, *, include_elo: bool) -> np.ndarray:
    def matrix(part: pd.DataFrame) -> np.ndarray:
        cols = ["market_prob", "pure_prob"] + (["elo_home_prob"] if include_elo else [])
        return np.column_stack([_logit(part[col]) for col in cols])
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=3000)
    model.fit(matrix(train), train["home_win"].astype(int))
    return model.predict_proba(matrix(test))[:, 1]


def _correct(prob: pd.Series, y: pd.Series) -> pd.Series:
    return (prob >= 0.5).astype(int).eq(y.astype(int))


def run(output_dir: str = "research_outputs/levline4_dynamic_strength_elo_v1") -> dict:
    frame = build_week_frozen_elo(_load())
    outputs: list[pd.DataFrame] = []
    coefficients_note = {
        "elo_k": ELO_K,
        "elo_home_advantage": ELO_HOME_ADVANTAGE,
        "offseason_regression_fraction_to_mean": OFFSEASON_REGRESSION,
        "within_week_outcome_updates_allowed": False,
    }

    for season in TARGET_SEASONS:
        train = frame[frame["season"] < season].copy()
        test = frame[frame["season"] == season].copy()
        if len(train) < 300 or test.empty:
            raise RuntimeError(f"insufficient season-forward data for {season}")
        test["fst_prob"] = _stack_predict(train, test, include_elo=False)
        test["fst_elo_prob"] = _stack_predict(train, test, include_elo=True)
        outputs.append(test)

    scored = pd.concat(outputs, ignore_index=True)
    if len(scored) != 1087:
        raise RuntimeError(f"expected 1087 target games, got {len(scored)}")
    scored["market_correct"] = _correct(scored["market_prob"], scored["home_win"])
    scored["elo_correct"] = _correct(scored["elo_home_prob"], scored["home_win"])
    scored["fst_correct"] = _correct(scored["fst_prob"], scored["home_win"])
    scored["fst_elo_correct"] = _correct(scored["fst_elo_prob"], scored["home_win"])
    scored["fst_side"] = (scored["fst_prob"] >= 0.5).astype(int)
    scored["fst_elo_side"] = (scored["fst_elo_prob"] >= 0.5).astype(int)
    disagree = scored[scored["fst_side"].ne(scored["fst_elo_side"])].copy()

    by_season = []
    for season, group in scored.groupby("season", sort=True):
        switches = group[group["fst_side"].ne(group["fst_elo_side"])]
        by_season.append({
            "season": int(season),
            "games": int(len(group)),
            "fst_correct": int(group["fst_correct"].sum()),
            "fst_elo_correct": int(group["fst_elo_correct"].sum()),
            "switches": int(len(switches)),
            "fst_elo_switch_correct": int(switches["fst_elo_correct"].sum()),
            "fst_switch_correct": int(switches["fst_correct"].sum()),
        })

    report = {
        "audit_id": "LEVLINE4-DYNAMIC-STRENGTH-ELO-V1",
        "status": "historical_exploratory_fixed_algorithm_not_promotion_proof",
        "governance": {
            "research_only": True,
            "fixed_elo_parameters_no_validation_grid_search": True,
            "completed_2026_outcomes_used": 0,
            "production_changed": False,
            "promotion_authorized": False,
        },
        "algorithm": coefficients_note,
        "sample": {"seasons": list(TARGET_SEASONS), "games": int(len(scored))},
        "results": {
            "market_correct": int(scored["market_correct"].sum()),
            "market_accuracy": float(scored["market_correct"].mean()),
            "standalone_elo_correct": int(scored["elo_correct"].sum()),
            "standalone_elo_accuracy": float(scored["elo_correct"].mean()),
            "fst_correct": int(scored["fst_correct"].sum()),
            "fst_accuracy": float(scored["fst_correct"].mean()),
            "fst_plus_elo_correct": int(scored["fst_elo_correct"].sum()),
            "fst_plus_elo_accuracy": float(scored["fst_elo_correct"].mean()),
            "fst_plus_elo_delta_pp": float((scored["fst_elo_correct"].mean() - scored["fst_correct"].mean()) * 100.0),
            "switches_vs_fst": int(len(disagree)),
            "fst_plus_elo_switch_correct": int(disagree["fst_elo_correct"].sum()),
            "fst_switch_correct": int(disagree["fst_correct"].sum()),
        },
        "by_season": by_season,
        "interpretation_policy": "A fixed Elo point estimate is descriptive only; no post-result K/HFA/offseason rescue search is authorized.",
        "promotion_authorized": False,
    }
    # Baseline drift invalidates the comparison.
    if report["results"]["market_correct"] != 735 or report["results"]["fst_correct"] != 741:
        raise RuntimeError(f"baseline reproduction drift: {report['results']}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out / "scored_games.csv", index=False)
    disagree.to_csv(out / "fst_elo_disagreements.csv", index=False)
    (out / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/levline4_dynamic_strength_elo_v1")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
