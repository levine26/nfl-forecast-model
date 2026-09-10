from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from types import SimpleNamespace
import numpy as np
import pandas as pd

from nfl_forecast.fst_production import (
    ACTIVE_PRODUCTION_STRATEGY,
    CANDIDATE_ID,
    LEGACY_PRODUCTION_STRATEGY,
    MODEL_VERSION,
    load_fst_artifact,
    legacy_final_home_probability,
    score_official_fst,
)
from nfl_forecast.market import add_vig_free_market_prob
from nfl_forecast.market_t120 import write_t120_market_research
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


def _legacy_diagnostics(p: pd.DataFrame) -> None:
    p["legacy_consistency_flag"] = p.apply(
        lambda r: "NEUTRAL"
        if abs(float(r["legacy_final_home_prob"]) - 0.5) < 0.02
        or abs(float(r["expected_margin"])) < 1.0
        else (
            "ALIGNED"
            if (float(r["legacy_final_home_prob"]) - 0.5) * float(r["expected_margin"]) > 0
            else "WIN-MARGIN SPLIT"
        ),
        axis=1,
    )
    p["legacy_confidence"] = p.apply(
        lambda r: confidence(
            r["legacy_final_home_prob"],
            r.get("model_disagreement", 0.0),
            r["legacy_consistency_flag"],
        ),
        axis=1,
    )
    p["consistency_flag"] = p["legacy_consistency_flag"]
    p["confidence"] = p["legacy_confidence"]
    p["confidence_diagnostic_scope"] = "legacy_75_25_pure_ensemble"


def _rescore_winner_probability(p: pd.DataFrame) -> None:
    if "pure_home_prob" not in p.columns:
        raise RuntimeError("Market refresh is missing legacy production PURE")
    if "legacy_pure_home_prob" not in p.columns:
        p["legacy_pure_home_prob"] = p["pure_home_prob"]

    legacy = legacy_final_home_probability(p["legacy_pure_home_prob"], p["market_home_prob"])
    p["legacy_final_home_prob"] = legacy

    if ACTIVE_PRODUCTION_STRATEGY == CANDIDATE_ID and "fst_pure_home_prob" in p.columns:
        fst_pure = pd.to_numeric(p["fst_pure_home_prob"], errors="coerce")
        if np.isfinite(fst_pure.to_numpy(dtype=float)).all():
            artifact = load_fst_artifact()
            scored = score_official_fst(
                p["legacy_pure_home_prob"],
                p["fst_pure_home_prob"],
                p["market_home_prob"],
                artifact,
            )
            p["final_home_prob"] = scored.final_home_prob
            p["legacy_final_home_prob"] = scored.legacy_final_home_prob
            p["market_available"] = scored.market_eligible
            p["fst_fallback"] = scored.fst_fallback
            p["fst_fallback_reason"] = scored.fst_fallback_reason
            p["fst_vs_market_delta"] = scored.fst_vs_market_delta
            p["fst_vs_legacy_delta"] = scored.fst_vs_legacy_delta
            p["final_probability_strategy"] = CANDIDATE_ID
            p["fst_artifact_id"] = CANDIDATE_ID
            p["fst_artifact_training_data_sha256"] = artifact.training_data_sha256
            p["fst_artifact_freeze_implementation_sha"] = artifact.freeze_implementation_sha
            p["model_version"] = MODEL_VERSION
            return

    if ACTIVE_PRODUCTION_STRATEGY not in {CANDIDATE_ID, LEGACY_PRODUCTION_STRATEGY}:
        raise RuntimeError(
            f"Unknown production probability strategy: {ACTIVE_PRODUCTION_STRATEGY!r}"
        )

    # Safe bridge for a market refresh that races the first full F-ST materialization,
    # and for the explicit one-line rollback regime. Never apply the frozen F-ST
    # coefficients to legacy pipeline PURE merely because nested PURE is absent.
    market = pd.to_numeric(p["market_home_prob"], errors="coerce")
    p["final_home_prob"] = legacy
    p["market_available"] = np.isfinite(market.to_numpy(dtype=float))
    p["fst_fallback"] = True
    if ACTIVE_PRODUCTION_STRATEGY == CANDIDATE_ID:
        p["fst_fallback_reason"] = "fst_nested_pure_not_materialized"
        p["final_probability_strategy"] = LEGACY_PRODUCTION_STRATEGY
        p["model_version"] = "0.9.0-pre-fst-materialization-fallback"
    else:
        p["fst_fallback_reason"] = "legacy_rollback_strategy_active"
        p["final_probability_strategy"] = LEGACY_PRODUCTION_STRATEGY
        p["model_version"] = MODEL_VERSION
    p["fst_vs_market_delta"] = np.nan
    p["fst_vs_legacy_delta"] = 0.0


def refresh(output_dir: str = "outputs", season: int = 2026) -> pd.DataFrame:
    path = Path(output_dir) / "this_week.csv"
    if not path.exists():
        raise RuntimeError("No existing full-model forecast. Run run_week.py first.")
    p = pd.read_csv(path)
    schedules = pd.read_csv(
        "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
        low_memory=False,
    )
    schedules = schedules[schedules["season"].eq(season)].copy()
    live = schedules[schedules["game_id"].isin(p["game_id"])].copy()
    live = add_vig_free_market_prob(live)
    idx = live.drop_duplicates("game_id", keep="last").set_index("game_id")

    fresh_market = (
        p["game_id"].map(idx["market_home_prob"])
        if "market_home_prob" in idx.columns
        else pd.Series(np.nan, index=p.index, dtype=float)
    )
    fresh_market_num = pd.to_numeric(fresh_market, errors="coerce")
    observed_market = pd.Series(
        np.isfinite(fresh_market_num.to_numpy(dtype=float)), index=p.index
    )

    for col in ["market_home_prob", "spread_line", "total_line"]:
        if col in idx.columns:
            fresh = p["game_id"].map(idx[col])
            if col in p.columns:
                p[col] = fresh.where(fresh.notna(), p[col])
            else:
                p[col] = fresh

    _rescore_winner_probability(p)
    p["fair_home_moneyline"] = p["final_home_prob"].map(fair_american_odds)
    p["pick"] = np.where(p["final_home_prob"] >= 0.5, p["home_team"], p["away_team"])
    p["model_edge"] = np.where(
        p["spread_line"].notna(), p["expected_margin"] - p["spread_line"], np.nan
    )
    if {"margin_sigma", "spread_line"}.issubset(p.columns):
        p["cover_home_prob"] = p.apply(
            lambda r: probability_above(r["spread_line"], r["expected_margin"], r["margin_sigma"]),
            axis=1,
        )
    if {"total_sigma", "total_line"}.issubset(p.columns):
        p["over_prob"] = p.apply(
            lambda r: probability_above(r["total_line"], r["expected_total"], r["total_sigma"]),
            axis=1,
        )

    _legacy_diagnostics(p)
    timestamp = datetime.now(timezone.utc).isoformat()
    previous_market_ts = (
        p["market_snapshot_timestamp_utc"].copy()
        if "market_snapshot_timestamp_utc" in p.columns
        else pd.Series(np.nan, index=p.index, dtype=object)
    )
    previous_market_source = (
        p["market_snapshot_source"].copy()
        if "market_snapshot_source" in p.columns
        else pd.Series(np.nan, index=p.index, dtype=object)
    )
    p["market_snapshot_timestamp_utc"] = previous_market_ts
    p.loc[observed_market, "market_snapshot_timestamp_utc"] = timestamp
    p["market_snapshot_source"] = previous_market_source
    p.loc[observed_market, "market_snapshot_source"] = "nflverse_games.csv_moneyline"
    usable_market = pd.Series(
        np.isfinite(pd.to_numeric(p["market_home_prob"], errors="coerce").to_numpy(dtype=float)),
        index=p.index,
    )
    p["market_freshness_status"] = "missing_or_invalid"
    p.loc[usable_market & ~observed_market, "market_freshness_status"] = "carried_forward_previous_snapshot"
    p.loc[observed_market, "market_freshness_status"] = "refreshed_this_run"
    p["snapshot_type"] = "MARKET"
    p["prediction_timestamp_utc"] = timestamp
    write_outputs(SimpleNamespace(predictions=p, games=schedules), output_dir)

    # Research only: reconstruct the last observed MARKET snapshot at or before
    # kickoff minus 120 minutes from append-only run history. Production never reads
    # this artifact, so instrumentation cannot change the published probability.
    write_t120_market_research(output_dir)
    return p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    p = refresh(args.output_dir, args.season)
    print(
        p[["away_team", "home_team", "final_home_prob", "pick", "model_edge", "confidence"]]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
