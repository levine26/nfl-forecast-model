from __future__ import annotations

"""Chronological evaluation of the Props 2.0 FTN matchup residual challenger.

The sportsbook probability is a fixed offset. FTN state is rebuilt strictly before
each target week. 2023-2025 results are retrospective development evidence only.
"""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from research.props.v2.props_ftn_matchup_state import (  # noqa: E402
    build_ftn_matchup_state,
    load_ftn_and_pbp,
)
from research.props.v2.props_ftn_market_residual import (  # noqa: E402
    COMMON_FEATURES,
    FEATURES_BY_PROP,
    apply_ftn_market_residual,
    fit_ftn_market_residual,
    no_vig_over_probability,
)

CONTRACT_VERSION = "levline-props-v2-ftn-residual-development-v0.1.0"
BOOTSTRAP_SEED = 20260918
SUPPORTED_PROPS = tuple(FEATURES_BY_PROP)
TEAM_ALIASES = {"JAC": "JAX", "LA": "LAR", "STL": "LAR", "WSH": "WAS"}


def _team(value) -> str:
    text = str(value or "").upper().strip()
    return TEAM_ALIASES.get(text, text)


def _read_inputs(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in paths]
    data = pd.concat(frames, ignore_index=True)
    if "p_over" not in data.columns and "v1_p_over" in data.columns:
        data["p_over"] = data["v1_p_over"]
    if "model_side" not in data.columns and "v1_model_side" in data.columns:
        data["model_side"] = data["v1_model_side"]
    required = {
        "season", "week", "game_id", "player_id", "team", "prop_type",
        "market_line", "over_odds", "under_odds", "p_over", "actual_result",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"forecast ledger missing fields: {sorted(missing)}")
    data["season"] = pd.to_numeric(data["season"], errors="raise").astype(int)
    data["week"] = pd.to_numeric(data["week"], errors="raise").astype(int)
    data["player_id"] = data["player_id"].astype(str)
    data["team"] = data["team"].map(_team)
    data["prop_type"] = data["prop_type"].astype(str)
    return data[data["prop_type"].isin(SUPPORTED_PROPS)].copy()


def _game_team_map(pbp: pd.DataFrame) -> dict[str, tuple[str, str]]:
    required = {"game_id", "posteam", "defteam"}
    missing = required - set(pbp.columns)
    if missing:
        raise ValueError(f"PBP missing game-team fields: {sorted(missing)}")
    work = pbp[["game_id", "posteam", "defteam"]].copy()
    work["game_id"] = work["game_id"].astype(str)
    work["posteam"] = work["posteam"].map(_team)
    work["defteam"] = work["defteam"].map(_team)
    work = work[
        work["posteam"].ne("")
        & work["defteam"].ne("")
        & work["posteam"].ne(work["defteam"])
    ]
    mapping: dict[str, tuple[str, str]] = {}
    for game_id, rows in work.groupby("game_id", sort=False):
        teams = sorted(set(rows["posteam"]) | set(rows["defteam"]))
        if len(teams) == 2:
            mapping[str(game_id)] = (teams[0], teams[1])
    return mapping


def _attach_ftn_state(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    min_season = int(data["season"].min())
    max_season = int(data["season"].max())
    history_seasons = list(range(max(2022, min_season - 1), max_season + 1))
    ftn, pbp = load_ftn_and_pbp(history_seasons)
    game_teams = _game_team_map(pbp)

    pieces: list[pd.DataFrame] = []
    audits: dict[str, dict] = {}
    rows_with_opponent = 0
    rows_with_state = 0

    for (season, week), group in data.groupby(["season", "week"], sort=True):
        target = group.copy()
        opponents = []
        for row in target.itertuples(index=False):
            teams = game_teams.get(str(row.game_id))
            opponent = ""
            if teams is not None:
                own = _team(row.team)
                if own == teams[0]:
                    opponent = teams[1]
                elif own == teams[1]:
                    opponent = teams[0]
            opponents.append(opponent)
        target["opponent"] = opponents
        rows_with_opponent += int(target["opponent"].ne("").sum())

        requested = sorted(
            set(target["team"].astype(str)) | set(target.loc[target["opponent"].ne(""), "opponent"])
        )
        state, audit = build_ftn_matchup_state(
            ftn,
            pbp,
            season=int(season),
            week=int(week),
            teams=requested,
        )
        key = f"{int(season)}-W{int(week):02d}"
        audits[key] = audit

        if state.empty:
            pieces.append(target)
            continue

        own_cols = ["team"] + [c for c in state.columns if c.startswith("ftn_off_")]
        own = state[own_cols].copy().rename(
            columns={
                "team": "_own_team",
                **{c: "own_off_" + c[len("ftn_off_"):] for c in own_cols if c != "team"},
            }
        )
        opp_cols = ["team"] + [c for c in state.columns if c.startswith("ftn_def_")]
        opp = state[opp_cols].copy().rename(
            columns={
                "team": "_opp_team",
                **{c: "opp_def_" + c[len("ftn_def_"):] for c in opp_cols if c != "team"},
            }
        )
        merged = target.merge(
            own, left_on="team", right_on="_own_team", how="left", validate="many_to_one"
        ).drop(columns=["_own_team"])
        merged = merged.merge(
            opp, left_on="opponent", right_on="_opp_team", how="left", validate="many_to_one"
        ).drop(columns=["_opp_team"])
        feature_cols = [c for c in merged.columns if c.startswith(("own_off_", "opp_def_"))]
        any_state = merged[feature_cols].notna().any(axis=1) if feature_cols else pd.Series(False, index=merged.index)
        rows_with_state += int(any_state.sum())
        pieces.append(merged)

    out = pd.concat(pieces, ignore_index=True)
    return out, {
        "history_seasons_loaded": history_seasons,
        "forecast_rows": int(len(out)),
        "rows_with_resolved_opponent": int(rows_with_opponent),
        "opponent_coverage": float(rows_with_opponent / len(out)) if len(out) else None,
        "rows_with_any_ftn_state": int(rows_with_state),
        "row_coverage": float(rows_with_state / len(out)) if len(out) else None,
        "period_audits": audits,
        "target_week_rows_used": 0,
        "completed_2026_outcomes_used_for_tuning": 0,
        "historical_exact_publication_timestamp_qualified": False,
        "live_source_capable": True,
    }


def _grade(scored: pd.DataFrame) -> pd.DataFrame:
    out = scored.copy()
    actual = pd.to_numeric(out["actual_result"], errors="raise").to_numpy(float)
    line = pd.to_numeric(out["market_line"], errors="raise").to_numpy(float)
    outcome = np.where(actual > line, "OVER", np.where(actual < line, "UNDER", "PUSH"))
    out["market_outcome_recomputed"] = outcome
    decided = out["market_outcome_recomputed"].ne("PUSH")

    market_p = np.asarray(
        [no_vig_over_probability(o, u) for o, u in zip(out["over_odds"], out["under_odds"])],
        dtype=float,
    )
    out["market_no_vig_p_over_eval"] = market_p
    informative = ~np.isclose(market_p, 0.5, atol=1e-12)
    out["market_side"] = pd.Series(pd.NA, index=out.index, dtype="object")
    out.loc[informative, "market_side"] = np.where(market_p[informative] > 0.5, "OVER", "UNDER")
    out["market_correct"] = np.where(
        decided & informative,
        out["market_side"].eq(out["market_outcome_recomputed"]).astype(float),
        np.nan,
    )

    if "model_side" in out.columns:
        v1_side = out["model_side"].where(out["model_side"].isin(["OVER", "UNDER"]))
    else:
        v1_side = pd.Series(np.where(pd.to_numeric(out["p_over"]) >= 0.5, "OVER", "UNDER"), index=out.index)
    out["v1_correct"] = np.where(
        decided & v1_side.notna(),
        v1_side.eq(out["market_outcome_recomputed"]).astype(float),
        np.nan,
    )
    out["ftn_correct"] = np.where(
        decided & out["ftn_challenger_side"].notna(),
        out["ftn_challenger_side"].eq(out["market_outcome_recomputed"]).astype(float),
        np.nan,
    )
    return out


def _score_models(frame: pd.DataFrame, models: dict) -> pd.DataFrame:
    return _grade(apply_ftn_market_residual(frame, models))


def _fit_models(train: pd.DataFrame, *, include_ftn: bool) -> tuple[dict, dict]:
    models, failures = {}, {}
    for prop in SUPPORTED_PROPS:
        try:
            features = None if include_ftn else COMMON_FEATURES
            models[prop] = fit_ftn_market_residual(
                train,
                prop_type=prop,
                feature_columns=features,
            )
        except Exception as exc:
            failures[prop] = f"{type(exc).__name__}: {exc}"
    return models, failures


def _merge_baseline_columns(ftn_scored: pd.DataFrame, base_scored: pd.DataFrame) -> pd.DataFrame:
    keys = ["season", "week", "game_id", "player_id", "prop_type", "market_line"]
    base = base_scored[
        keys + ["ftn_challenger_p_over", "ftn_challenger_side", "ftn_correct"]
    ].copy()
    base = base.rename(
        columns={
            "ftn_challenger_p_over": "matched_baseline_p_over",
            "ftn_challenger_side": "matched_baseline_side",
            "ftn_correct": "matched_baseline_correct",
        }
    )
    return ftn_scored.merge(base, on=keys, how="left", validate="one_to_one")


def _log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(np.asarray(p, float), 1e-8, 1.0 - 1e-8)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def _metrics(frame: pd.DataFrame) -> dict:
    work = frame[
        frame["market_outcome_recomputed"].ne("PUSH")
        & frame["ftn_correct"].notna()
        & frame["matched_baseline_correct"].notna()
    ].copy()
    if work.empty:
        return {"n": 0}
    y = work["market_outcome_recomputed"].eq("OVER").astype(float).to_numpy()
    market_p = work["market_no_vig_p_over_eval"].to_numpy(float)
    v1_p = pd.to_numeric(work["p_over"], errors="raise").to_numpy(float)
    ftn_p = work["ftn_challenger_p_over"].to_numpy(float)
    baseline_p = work["matched_baseline_p_over"].to_numpy(float)
    market_info = work["market_correct"].notna()
    return {
        "n": int(len(work)),
        "unique_games": int(work["game_id"].astype(str).nunique()),
        "unique_players": int(work["player_id"].astype(str).nunique()),
        "ftn_accuracy": float(work["ftn_correct"].mean()),
        "matched_market_v1_residual_accuracy": float(work["matched_baseline_correct"].mean()),
        "v1_accuracy": float(work["v1_correct"].mean()),
        "market_price_direction_rows": int(market_info.sum()),
        "market_price_tie_rows": int((~market_info).sum()),
        "market_price_direction_accuracy": (
            float(work.loc[market_info, "market_correct"].mean()) if market_info.any() else None
        ),
        "ftn_on_market_informative_rows_accuracy": (
            float(work.loc[market_info, "ftn_correct"].mean()) if market_info.any() else None
        ),
        "ftn_minus_matched_baseline_pp": float(
            100.0 * (work["ftn_correct"] - work["matched_baseline_correct"]).mean()
        ),
        "ftn_minus_v1_pp": float(100.0 * (work["ftn_correct"] - work["v1_correct"]).mean()),
        "ftn_minus_market_informative_pp": (
            float(
                100.0
                * (
                    work.loc[market_info, "ftn_correct"]
                    - work.loc[market_info, "market_correct"]
                ).mean()
            )
            if market_info.any()
            else None
        ),
        "ftn_brier": _brier(y, ftn_p),
        "matched_baseline_brier": _brier(y, baseline_p),
        "market_brier": _brier(y, market_p),
        "v1_brier": _brier(y, v1_p),
        "ftn_log_loss": _log_loss(y, ftn_p),
        "matched_baseline_log_loss": _log_loss(y, baseline_p),
        "market_log_loss": _log_loss(y, market_p),
        "v1_log_loss": _log_loss(y, v1_p),
    }


def _cluster_bootstrap(frame: pd.DataFrame, replicates: int, seed: int) -> dict:
    work = frame[
        frame["market_outcome_recomputed"].ne("PUSH")
        & frame["ftn_correct"].notna()
        & frame["matched_baseline_correct"].notna()
    ].copy()
    games = np.asarray(sorted(work["game_id"].astype(str).unique()))
    if len(games) < 2:
        return {
            "ftn_accuracy_ci95": [None, None],
            "ftn_minus_baseline_ci95_pp": [None, None],
        }
    grouped = {g: work[work["game_id"].astype(str).eq(g)] for g in games}
    rng = np.random.default_rng(seed)
    acc = np.empty(replicates)
    diff = np.empty(replicates)
    for i in range(replicates):
        sample = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[g] for g in sample], ignore_index=True)
        acc[i] = float(boot["ftn_correct"].mean())
        diff[i] = float(
            100.0 * (boot["ftn_correct"] - boot["matched_baseline_correct"]).mean()
        )
    return {
        "ftn_accuracy_ci95": [float(np.quantile(acc, .025)), float(np.quantile(acc, .975))],
        "ftn_minus_baseline_ci95_pp": [
            float(np.quantile(diff, .025)), float(np.quantile(diff, .975))
        ],
    }


def _evaluate_block(
    train: pd.DataFrame,
    evaluate: pd.DataFrame,
    *,
    replicates: int,
    seed: int,
):
    ftn_models, ftn_fail = _fit_models(train, include_ftn=True)
    base_models, base_fail = _fit_models(train, include_ftn=False)
    common = sorted(set(ftn_models) & set(base_models))
    if not common:
        raise ValueError("no prop family produced both FTN and matched baseline models")
    ftn_models = {k: ftn_models[k] for k in common}
    base_models = {k: base_models[k] for k in common}
    eval_common = evaluate[evaluate["prop_type"].isin(common)].copy()
    ftn_scored = _score_models(eval_common, ftn_models)
    base_scored = _score_models(eval_common, base_models)
    paired = _merge_baseline_columns(ftn_scored, base_scored)
    overall = _metrics(paired)
    overall.update(_cluster_bootstrap(paired, replicates, seed))
    overall["by_prop_type"] = {
        str(prop): _metrics(group) for prop, group in paired.groupby("prop_type", sort=True)
    }
    return paired, {
        "models": {k: v.to_dict() for k, v in ftn_models.items()},
        "matched_baseline_models": {k: v.to_dict() for k, v in base_models.items()},
        "ftn_fit_failures": ftn_fail,
        "baseline_fit_failures": base_fail,
        "evaluation": overall,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=3000)
    args = parser.parse_args()
    if args.bootstrap_replicates <= 0:
        raise ValueError("--bootstrap-replicates must be positive")

    data = _read_inputs(args.input)
    data, coverage = _attach_ftn_state(data)

    fixed_train = data[data["season"].eq(2023) & data["week"].le(9)].copy()
    fixed_eval = data[
        (data["season"].eq(2023) & data["week"].ge(10))
        | data["season"].isin([2024, 2025])
    ].copy()
    fixed_rows, fixed = _evaluate_block(
        fixed_train,
        fixed_eval,
        replicates=args.bootstrap_replicates,
        seed=BOOTSTRAP_SEED,
    )

    rolling_rows = []
    rolling = {}
    for season in (2024, 2025):
        train = data[data["season"].ge(2023) & data["season"].lt(season)].copy()
        evaluate = data[data["season"].eq(season)].copy()
        if train.empty or evaluate.empty:
            continue
        rows, result = _evaluate_block(
            train,
            evaluate,
            replicates=args.bootstrap_replicates,
            seed=BOOTSTRAP_SEED + season,
        )
        rows["evaluation_season"] = season
        rolling_rows.append(rows)
        rolling[str(season)] = result

    fixed_eval_metrics = fixed["evaluation"]
    rolling_2024 = rolling.get("2024", {}).get("evaluation", {})
    ci = fixed_eval_metrics.get("ftn_minus_baseline_ci95_pp", [None, None])
    decision_positive = bool(
        fixed_eval_metrics.get("ftn_minus_matched_baseline_pp", 0.0) > 0
        and ci[0] is not None
        and ci[0] > 0
        and rolling_2024.get("ftn_minus_matched_baseline_pp", 0.0) > 0
    )

    payload = {
        "contract_version": CONTRACT_VERSION,
        "research_label": "RETROSPECTIVE CHALLENGER DEVELOPMENT - NOT PROMOTION EVIDENCE",
        "promotion_authorized": False,
        "selective_threshold_used": False,
        "completed_2026_outcomes_used_for_tuning": 0,
        "ftn_state_coverage": coverage,
        "fixed_anchor": {
            "training_rule": "2023 Weeks 1-9 only; fixed thereafter",
            **fixed,
        },
        "rolling_origin": {
            "training_rule": "target season uses only prior seasons beginning 2023",
            "by_evaluation_season": rolling,
        },
        "preregistered_incremental_signal_decision": {
            "positive": decision_positive,
            "rule": (
                "fixed-anchor FTN-minus-baseline > 0; fixed-anchor game-clustered "
                "95% CI lower bound > 0; and 2024 rolling-origin FTN-minus-baseline > 0"
            ),
            "production_promotion_authorized_by_decision": False,
        },
        "interpretation": (
            "The matched baseline uses the same prop partition, market offset, regularization, "
            "and frozen LevLine probability gap but excludes FTN features. FTN-minus-baseline "
            "is therefore the primary incremental matchup diagnostic."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fixed_rows.to_csv(args.output_dir / "fixed_anchor_rows.csv", index=False)
    if rolling_rows:
        pd.concat(rolling_rows, ignore_index=True).to_csv(
            args.output_dir / "rolling_origin_rows.csv", index=False
        )
    print(json.dumps({
        "fixed_anchor": payload["fixed_anchor"]["evaluation"],
        "rolling_origin": {
            k: v["evaluation"] for k, v in rolling.items()
        },
        "coverage": {
            "forecast_rows": coverage["forecast_rows"],
            "rows_with_any_ftn_state": coverage["rows_with_any_ftn_state"],
            "row_coverage": coverage["row_coverage"],
            "opponent_coverage": coverage["opponent_coverage"],
        },
        "incremental_signal_positive": decision_positive,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
