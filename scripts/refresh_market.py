from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from types import SimpleNamespace
import numpy as np
import pandas as pd

from nfl_forecast.market import add_vig_free_market_prob
from nfl_forecast.publish import write_outputs


def fair_american_odds(prob: float) -> float:
    p = float(np.clip(prob, 1e-6, 1 - 1e-6))
    return -100.0 * p / (1.0 - p) if p >= 0.5 else 100.0 * (1.0 - p) / p


def probability_above(threshold, mean, sigma) -> float:
    if pd.isna(threshold) or pd.isna(mean) or pd.isna(sigma) or float(sigma) <= 0:
        return np.nan
    return float(1.0 - NormalDist(mu=float(mean), sigma=float(sigma)).cdf(float(threshold)))


def confidence(prob: float, disagreement: float, flag: str) -> str:
    q = max(float(prob), 1.0 - float(prob))
    level = 3 if q >= 0.70 else 2 if q >= 0.60 else 1 if q >= 0.55 else 0
    if float(disagreement) >= 0.10:
        level -= 1
    if flag == "WIN-MARGIN SPLIT":
        level -= 1
    return ["Coin Flip", "Lean", "Solid", "High"][max(0, min(3, level))]


def refresh(output_dir: str = "outputs", season: int = 2026) -> pd.DataFrame:
    path = Path(output_dir) / "this_week.csv"
    if not path.exists():
        raise RuntimeError("No existing full-model forecast. Run run_week.py first.")
    p = pd.read_csv(path)
    schedules = pd.read_csv("https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv", low_memory=False)
    schedules = schedules[schedules["season"].eq(season)].copy()
    live = schedules[schedules["game_id"].isin(p["game_id"])].copy()
    live = add_vig_free_market_prob(live)
    idx = live.drop_duplicates("game_id", keep="last").set_index("game_id")

    for col in ["market_home_prob", "spread_line", "total_line"]:
        if col in idx.columns:
            fresh = p["game_id"].map(idx[col])
            if col in p.columns:
                p[col] = fresh.where(fresh.notna(), p[col])
            else:
                p[col] = fresh

    has_market = p["market_home_prob"].notna()
    p["market_available"] = has_market
    p["final_home_prob"] = p["pure_home_prob"]
    p.loc[has_market, "final_home_prob"] = (
        0.75 * p.loc[has_market, "pure_home_prob"] + 0.25 * p.loc[has_market, "market_home_prob"]
    )
    p["fair_home_moneyline"] = p["final_home_prob"].map(fair_american_odds)
    p["pick"] = np.where(p["final_home_prob"] >= 0.5, p["home_team"], p["away_team"])
    p["model_edge"] = np.where(p["spread_line"].notna(), p["expected_margin"] - p["spread_line"], np.nan)
    if {"margin_sigma", "spread_line"}.issubset(p.columns):
        p["cover_home_prob"] = p.apply(lambda r: probability_above(r["spread_line"], r["expected_margin"], r["margin_sigma"]), axis=1)
    if {"total_sigma", "total_line"}.issubset(p.columns):
        p["over_prob"] = p.apply(lambda r: probability_above(r["total_line"], r["expected_total"], r["total_sigma"]), axis=1)

    p["consistency_flag"] = p.apply(
        lambda r: "NEUTRAL" if abs(float(r["final_home_prob"]) - 0.5) < 0.02 or abs(float(r["expected_margin"])) < 1.0
        else ("ALIGNED" if (float(r["final_home_prob"]) - 0.5) * float(r["expected_margin"]) > 0 else "WIN-MARGIN SPLIT"),
        axis=1,
    )
    p["confidence"] = p.apply(
        lambda r: confidence(r["final_home_prob"], r.get("model_disagreement", 0.0), r["consistency_flag"]), axis=1
    )
    p["snapshot_type"] = "MARKET"
    p["prediction_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    write_outputs(SimpleNamespace(predictions=p, games=schedules), output_dir)
    return p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    p = refresh(args.output_dir, args.season)
    print(p[["away_team","home_team","final_home_prob","pick","model_edge","confidence"]].to_string(index=False))


if __name__ == "__main__":
    main()
