from __future__ import annotations

"""Chronological evaluation of the NGS + sportsbook-prior Props challenger.

Inputs are frozen V1 forecast-level historical ledgers. For every forecast week this
runner attaches only NGS state from strictly earlier weeks, then evaluates a regularized
market-offset residual model in rolling-origin season blocks.

2023-2025 are development evidence only. No selective betting threshold is used.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from research.props.v2.props_ngs_efficiency_state import (
    build_lagged_ngs_state,
    load_ngs_efficiency_history,
)
from research.props.v2.props_ngs_market_residual import (
    FEATURES_BY_PROP,
    RESEARCH_LABEL,
    add_market_features,
    apply_ngs_market_residual,
    fit_ngs_market_residual,
)

CONTRACT_VERSION = "levline-props-v2-ngs-market-residual-development-v0.1.0"
BOOTSTRAP_SEED = 20260918
BOOTSTRAP_REPLICATES = 3000
SUPPORTED_PROPS = tuple(FEATURES_BY_PROP)


def _fingerprint(path: Path) -> dict:
    raw = path.read_bytes()
    return {
        "path": str(path),
        "bytes": len(raw),
        "sha256": sha256(raw).hexdigest(),
    }


def _load_inputs(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_csv(path, dtype={"player_id": "string", "game_id": "string"})
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    required = {
        "season",
        "week",
        "game_id",
        "player_id",
        "prop_type",
        "market_line",
        "over_odds",
        "under_odds",
        "p_over",
        "model_side",
        "actual_result",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"frozen forecast ledger missing fields: {sorted(missing)}")
    data["season"] = pd.to_numeric(data["season"], errors="raise").astype(int)
    data["week"] = pd.to_numeric(data["week"], errors="raise").astype(int)
    data["player_id"] = data["player_id"].astype("string").fillna("").str.strip()
    data = data[
        data["season"].between(2023, 2025)
        & data["week"].between(1, 18)
        & data["prop_type"].astype(str).isin(SUPPORTED_PROPS)
        & data["player_id"].ne("")
    ].copy()
    return data.reset_index(drop=True)


def attach_strictly_lagged_ngs(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    raw = load_ngs_efficiency_history([2022, 2023, 2024, 2025])
    pieces = []
    audits = {}
    for (season, week), group in data.groupby(["season", "week"], sort=True):
        player_ids = sorted(set(group["player_id"].astype(str)))
        state, audit = build_lagged_ngs_state(
            passing=raw["passing"],
            receiving=raw["receiving"],
            rushing=raw["rushing"],
            season=int(season),
            week=int(week),
            player_ids=player_ids,
        )
        key = f"{int(season)}-W{int(week)}"
        audits[key] = audit
        if state.empty:
            enriched = group.copy()
        else:
            enriched = group.merge(
                state,
                left_on="player_id",
                right_on="player_id",
                how="left",
                validate="many_to_one",
            )
        pieces.append(enriched)
    out = pd.concat(pieces, ignore_index=True)
    feature_columns = sorted(
        {
            column
            for columns in FEATURES_BY_PROP.values()
            for column in columns
        }
    )
    for column in feature_columns:
        if column not in out.columns:
            out[column] = np.nan
    return out, {
        "periods": audits,
        "target_week_rows_used": 0,
        "completed_2026_outcomes_used": 0,
        "rows": int(len(out)),
        "rows_with_any_ngs_feature": int(
            out[feature_columns].notna().any(axis=1).sum()
        ),
    }


def _outcome(frame: pd.DataFrame) -> pd.Series:
    actual = pd.to_numeric(frame["actual_result"], errors="coerce")
    line = pd.to_numeric(frame["market_line"], errors="coerce")
    return pd.Series(
        np.where(actual > line, "OVER", np.where(actual < line, "UNDER", "PUSH")),
        index=frame.index,
    )


def _log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(np.asarray(p, float), 1e-8, 1.0 - 1e-8)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _metrics(frame: pd.DataFrame) -> dict:
    work = frame.copy()
    work["market_outcome"] = _outcome(work)
    work = work[work["market_outcome"].isin(["OVER", "UNDER"])].copy()
    work = work[work["ngs_challenger_side"].isin(["OVER", "UNDER"])].copy()
    if work.empty:
        return {"n": 0}

    market = add_market_features(work)
    y = market["market_outcome"].eq("OVER").astype(float).to_numpy()
    market_p = market["market_no_vig_p_over"].to_numpy(float)
    market_side = np.where(
        market_p > 0.5 + 1e-12,
        "OVER",
        np.where(market_p < 0.5 - 1e-12, "UNDER", None),
    )
    v1_correct = work["model_side"].eq(work["market_outcome"]).astype(float)
    market_informative = pd.Series(
        pd.notna(market_side), index=work.index, dtype=bool
    )
    market_correct = pd.Series(np.nan, index=work.index, dtype=float)
    market_correct.loc[market_informative] = (
        market_side[market_informative.to_numpy()]
        == work.loc[market_informative, "market_outcome"].to_numpy()
    ).astype(float)
    challenger_correct = work["ngs_challenger_side"].eq(
        work["market_outcome"]
    ).astype(float)
    challenger_market = challenger_correct.loc[market_informative]
    market_direction = market_correct.loc[market_informative]

    return {
        "n": int(len(work)),
        "games": int(work["game_id"].astype(str).nunique()),
        "players": int(work["player_id"].astype(str).nunique()),
        "v1_accuracy": float(v1_correct.mean()),
        "market_price_direction_rows": int(market_informative.sum()),
        "market_price_tie_rows": int((~market_informative).sum()),
        "market_price_accuracy": (
            float(market_direction.mean()) if len(market_direction) else None
        ),
        "ngs_challenger_accuracy": float(challenger_correct.mean()),
        "ngs_minus_v1_accuracy": float((challenger_correct - v1_correct).mean()),
        "ngs_on_market_informative_rows_accuracy": (
            float(challenger_market.mean()) if len(challenger_market) else None
        ),
        "ngs_minus_market_accuracy": (
            float((challenger_market - market_direction).mean())
            if len(market_direction)
            else None
        ),
        "v1_brier": float(np.mean((work["p_over"].to_numpy(float) - y) ** 2)),
        "market_brier": float(
            np.mean((market["market_no_vig_p_over"].to_numpy(float) - y) ** 2)
        ),
        "ngs_brier": float(
            np.mean((work["ngs_challenger_p_over"].to_numpy(float) - y) ** 2)
        ),
        "v1_log_loss": _log_loss(y, work["p_over"].to_numpy(float)),
        "market_log_loss": _log_loss(
            y, market["market_no_vig_p_over"].to_numpy(float)
        ),
        "ngs_log_loss": _log_loss(
            y, work["ngs_challenger_p_over"].to_numpy(float)
        ),
        "v1_correct_vector": v1_correct.to_numpy(float),
        "market_correct_vector": market_correct.to_numpy(float),
        "challenger_correct_vector": challenger_correct.to_numpy(float),
    }


def _cluster_ci(frame: pd.DataFrame, *, baseline: str, seed: int) -> list[float | None]:
    work = frame.copy()
    work["market_outcome"] = _outcome(work)
    work = work[
        work["market_outcome"].isin(["OVER", "UNDER"])
        & work["ngs_challenger_side"].isin(["OVER", "UNDER"])
    ].copy()
    if baseline == "v1":
        base_correct = work["model_side"].eq(work["market_outcome"]).astype(float)
    elif baseline == "market":
        priced = add_market_features(work)
        market_p = priced["market_no_vig_p_over"].to_numpy(float)
        market_side = np.where(
            market_p > 0.5 + 1e-12,
            "OVER",
            np.where(market_p < 0.5 - 1e-12, "UNDER", None),
        )
        informative = pd.notna(market_side)
        base_correct = pd.Series(np.nan, index=work.index, dtype=float)
        base_correct.loc[informative] = (
            market_side[informative]
            == work.loc[informative, "market_outcome"].to_numpy()
        ).astype(float)
    else:
        raise ValueError("baseline must be v1 or market")
    work["_base"] = base_correct
    work["_challenger"] = work["ngs_challenger_side"].eq(
        work["market_outcome"]
    ).astype(float)

    games = np.asarray(sorted(work["game_id"].astype(str).unique()))
    if len(games) < 2:
        return [None, None]
    grouped = {g: work[work["game_id"].astype(str).eq(g)] for g in games}
    rng = np.random.default_rng(seed)
    diffs = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
    for i in range(BOOTSTRAP_REPLICATES):
        sampled = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[g] for g in sampled], ignore_index=True)
        diffs[i] = float((boot["_challenger"] - boot["_base"]).mean())
    return [
        float(np.quantile(diffs, 0.025)),
        float(np.quantile(diffs, 0.975)),
    ]


def _strip_vectors(metrics: dict) -> dict:
    return {
        key: value
        for key, value in metrics.items()
        if not key.endswith("_vector")
    }


def evaluate(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    scored_parts = []
    models_by_season = {}
    for season in (2024, 2025):
        train = data[data["season"].lt(season)].copy()
        test = data[data["season"].eq(season)].copy()
        if train.empty or test.empty:
            continue
        models = {}
        model_meta = {}
        for prop in SUPPORTED_PROPS:
            try:
                model = fit_ngs_market_residual(
                    train,
                    prop_type=prop,
                )
            except Exception as exc:
                model_meta[prop] = {
                    "status": "unavailable",
                    "reason": f"{type(exc).__name__}: {str(exc)[:300]}",
                }
                continue
            models[prop] = model
            model_meta[prop] = {
                "status": "fitted",
                "training_season_min": int(train["season"].min()),
                "training_season_max": int(train["season"].max()),
                "evaluation_season": int(season),
                "model": model.to_dict(),
            }
        if not models:
            continue
        scored = apply_ngs_market_residual(test, models)
        scored["evaluation_season"] = season
        scored_parts.append(scored)
        models_by_season[str(season)] = model_meta

    if not scored_parts:
        raise ValueError("no rolling-origin NGS market residual evaluations were available")
    scored = pd.concat(scored_parts, ignore_index=True)
    evaluated = scored[scored["ngs_challenger_side"].notna()].copy()

    summary = _strip_vectors(_metrics(evaluated))
    summary["ngs_minus_v1_game_clustered_ci95"] = _cluster_ci(
        evaluated,
        baseline="v1",
        seed=BOOTSTRAP_SEED,
    )
    summary["ngs_minus_market_game_clustered_ci95"] = _cluster_ci(
        evaluated,
        baseline="market",
        seed=BOOTSTRAP_SEED + 1,
    )
    summary["by_season"] = {}
    for season, group in evaluated.groupby("evaluation_season", sort=True):
        summary["by_season"][str(int(season))] = _strip_vectors(_metrics(group))
    summary["by_prop"] = {}
    for prop, group in evaluated.groupby("prop_type", sort=True):
        summary["by_prop"][str(prop)] = _strip_vectors(_metrics(group))

    return scored, {
        "contract_version": CONTRACT_VERSION,
        "research_label": RESEARCH_LABEL,
        "promotion_authorized": False,
        "selective_threshold_used": False,
        "hyperparameter_search_performed": False,
        "market_coefficient_fixed_as_offset": True,
        "rolling_origin_models": models_by_season,
        "evaluation": summary,
        "interpretation": (
            "Retrospective development evidence only. 2023-2025 outcomes were already "
            "inspected during V1 diagnosis and cannot authorize production promotion."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    data = _load_inputs(args.input)
    enriched, ngs_audit = attach_strictly_lagged_ngs(data)
    scored, result = evaluate(enriched)
    result["input_provenance"] = [_fingerprint(path) for path in args.input]
    result["ngs_state_audit"] = ngs_audit

    args.output_dir.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(args.output_dir / "ngs_enriched_rows.csv", index=False)
    scored.to_csv(args.output_dir / "scored_rows.csv", index=False)
    (args.output_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["evaluation"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
