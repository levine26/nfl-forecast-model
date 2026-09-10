from __future__ import annotations

"""Write cumulative prospective evaluation for frozen F-ST-01 locks.

Before production promotion, the shadow ledger's production probability is the legacy
75/25 comparator. After promotion, the official lock is F-ST itself, so this evaluator
joins the immutable production lock and substitutes its separately persisted legacy
counterfactual as the reference. It never treats F-ST-vs-F-ST zero delta as evidence.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_fst import FROZEN_CANDIDATE_ID
from nfl_forecast.challenger_prospective import evaluate_frozen_fst


def _attach_production_regime(history: pd.DataFrame, official_path: Path) -> pd.DataFrame:
    if not official_path.exists() or history.empty:
        return history
    official = pd.read_csv(official_path)
    if "game_id" not in official.columns:
        return history
    wanted = [
        c for c in [
            "game_id", "final_home_prob", "legacy_final_home_prob", "fst_pure_home_prob",
            "market_home_prob", "final_probability_strategy", "model_version",
        ]
        if c in official.columns
    ]
    official = official[wanted].drop_duplicates("game_id", keep="last").rename(columns={
        "final_home_prob": "_official_final_home_prob",
        "legacy_final_home_prob": "_official_legacy_final_home_prob",
        "fst_pure_home_prob": "_official_fst_pure_home_prob",
        "market_home_prob": "_official_market_home_prob",
        "final_probability_strategy": "_official_probability_strategy",
        "model_version": "_official_model_version",
    })
    merged = history.merge(official, on="game_id", how="left")

    def numeric_series(name: str) -> pd.Series:
        if name not in merged.columns:
            return pd.Series(np.nan, index=merged.index, dtype=float)
        return pd.to_numeric(merged[name], errors="coerce")

    promoted = merged.get(
        "_official_probability_strategy", pd.Series("", index=merged.index)
    ).astype(str).eq(FROZEN_CANDIDATE_ID)
    legacy = numeric_series("_official_legacy_final_home_prob")
    official_final = numeric_series("_official_final_home_prob")
    official_market = numeric_series("_official_market_home_prob")
    official_pure = numeric_series("_official_fst_pure_home_prob")
    usable = promoted & legacy.notna() & official_final.notna()

    if usable.any():
        # Preserve raw shadow values for audit before presenting the normalized evaluator view.
        merged["shadow_research_fst_home_prob"] = merged["challenger_final_home_prob"]
        merged["shadow_production_final_home_prob"] = merged["production_final_home_prob"]
        merged.loc[usable, "challenger_final_home_prob"] = official_final.loc[usable]
        merged.loc[usable, "production_final_home_prob"] = legacy.loc[usable]
        if "market_home_prob_t120" in merged.columns:
            market_mask = usable & official_market.notna()
            merged.loc[market_mask, "market_home_prob_t120"] = official_market.loc[market_mask]
        if "challenger_pure_home_prob" in merged.columns:
            pure_mask = usable & official_pure.notna()
            merged.loc[pure_mask, "challenger_pure_home_prob"] = official_pure.loc[pure_mask]
        merged["evaluation_reference"] = "predeployment_shadow_production"
        merged.loc[usable, "evaluation_reference"] = "locked_legacy_75_25_counterfactual"
        merged["evaluation_fst_source"] = "research_shadow"
        merged.loc[usable, "evaluation_fst_source"] = "official_production_lock"
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow-history", default="challenger_outputs/prediction_history_shadow.csv")
    parser.add_argument("--official-history", default="outputs/prediction_history.csv")
    parser.add_argument("--output-dir", default="challenger_outputs/fst")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    args = parser.parse_args()

    history_path = Path(args.shadow_history)
    if not history_path.exists():
        raise SystemExit(f"Missing challenger shadow history: {history_path}")
    history = _attach_production_regime(
        pd.read_csv(history_path),
        Path(args.official_history),
    )
    report, weekly = evaluate_frozen_fst(
        history,
        bootstrap_samples=args.bootstrap_samples,
    )
    report["post_promotion_reference"] = "legacy_75_25_counterfactual_from_official_lock"
    report["post_promotion_fst_source"] = "official_F-ST_lock"
    report["zero_delta_F-ST_vs_F-ST_is_evidence"] = False
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "prospective_evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    weekly.to_csv(out / "prospective_weekly.csv", index=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
