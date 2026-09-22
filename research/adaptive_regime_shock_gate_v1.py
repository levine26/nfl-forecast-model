from __future__ import annotations

"""Candidate 2: point-in-time regime-change / information-shock gate.

Research-only implementation of ADAPTIVE-REGIME-SHOCK-GATE-V1.

The candidate preserves frozen F-ST unless:
1. F-ST is near the winner boundary;
2. the registered component-resolved challenger chooses the opposite side; and
3. a separately observed T-120 personnel discontinuity authorizes a switch.

The personnel channel never chooses switch direction and no arbitrary injury points are
assigned. Missing or ambiguous state fails closed to the incumbent.

No completed 2026 outcomes are used. Production surfaces are not imported or mutated.
"""

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from research.adaptive_naive_weekly_refit_control_v1 import (
    attach_frozen_fst,
    load_frame as load_weekly_refit_frame,
    weekly_refit_predictions,
)
from research.adaptive_residual_state_v1 import load_fst_replay, run_state_filter
from nfl_forecast.availability_2025_reconstruction import normalize_practice_status

FST_SOURCE = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
COMPONENT_SOURCE = Path("challenger_outputs/fst/provenance/base_oof_keyed.csv")
TARGET_SEASONS = (2022, 2023, 2024, 2025)
COMPONENTS = ("logistic", "extra_trees", "xgboost", "catboost")
CANDIDATE_ID = "ADAPTIVE-REGIME-SHOCK-GATE-V1"
EPS = 1e-6
PRIMARY_BOUNDARY = 0.075
PRIMARY_OL_NEW_THRESHOLD = 2
PRIMARY_PRACTICE_MODE = "dnp_only"
TEAM_ALIASES = {"JAC": "JAX", "LAR": "LA", "WSH": "WAS", "OAK": "LV"}


@dataclass(frozen=True)
class GateConfig:
    boundary: float = PRIMARY_BOUNDARY
    ol_new_threshold: int = PRIMARY_OL_NEW_THRESHOLD
    practice_mode: str = PRIMARY_PRACTICE_MODE
    include_qb_change: bool = True
    include_ol_churn: bool = True
    include_qb_practice: bool = True


PRIMARY_CONFIG = GateConfig()


def _normalize_team(value: object) -> str:
    code = str(value or "").strip().upper()
    return TEAM_ALIASES.get(code, code)


def _logit(values: Iterable[float] | pd.Series | np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def _log_loss(probability: pd.Series, outcome: pd.Series) -> float:
    p = np.clip(pd.to_numeric(probability, errors="raise").to_numpy(float), EPS, 1.0 - EPS)
    y = pd.to_numeric(outcome, errors="raise").to_numpy(float)
    return float(np.mean(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))))


def build_component_challenger(
    component_path: str | Path = COMPONENT_SOURCE,
    fst_path: str | Path = FST_SOURCE,
) -> pd.DataFrame:
    """Reconstruct the registered component-resolved season-forward L2 challenger."""
    base = pd.read_csv(component_path).copy()
    market = pd.read_csv(fst_path).copy()

    required_base = {"game_id", "season", "home_win", *COMPONENTS}
    required_market = {"game_id", "season", "home_win", "market_prob"}
    missing_base = required_base - set(base.columns)
    missing_market = required_market - set(market.columns)
    if missing_base:
        raise ValueError(f"component OOF source missing fields: {sorted(missing_base)}")
    if missing_market:
        raise ValueError(f"F-ST provenance source missing fields: {sorted(missing_market)}")
    if base["game_id"].astype(str).duplicated().any():
        raise ValueError("component OOF source contains duplicate game IDs")
    if market["game_id"].astype(str).duplicated().any():
        raise ValueError("F-ST provenance source contains duplicate game IDs")

    base = base[["game_id", "season", "home_win", *COMPONENTS]].copy()
    market = market[["game_id", "season", "home_win", "market_prob"]].copy()
    work = base.merge(
        market,
        on="game_id",
        how="inner",
        suffixes=("_component", "_market"),
        validate="one_to_one",
    )

    season_component = pd.to_numeric(work["season_component"], errors="coerce")
    season_market = pd.to_numeric(work["season_market"], errors="coerce")
    outcome_component = pd.to_numeric(work["home_win_component"], errors="coerce")
    outcome_market = pd.to_numeric(work["home_win_market"], errors="coerce")
    if not np.array_equal(season_component.to_numpy(), season_market.to_numpy(), equal_nan=True):
        raise ValueError("component/F-ST season identity mismatch")
    if not np.array_equal(outcome_component.to_numpy(), outcome_market.to_numpy(), equal_nan=True):
        raise ValueError("component/F-ST outcome identity mismatch")

    work["season"] = season_component.astype(int)
    work["home_win"] = outcome_component.astype(int)
    for column in ("market_prob", *COMPONENTS):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    valid = work["home_win"].isin([0, 1])
    for column in ("market_prob", *COMPONENTS):
        valid &= work[column].gt(0.0) & work[column].lt(1.0)
    work = work.loc[valid].copy()
    if work.empty:
        raise ValueError("component reconstruction has no usable rows")

    feature_cols = ["market_logit", *[f"{name}_logit" for name in COMPONENTS]]
    work["market_logit"] = _logit(work["market_prob"])
    for name in COMPONENTS:
        work[f"{name}_logit"] = _logit(work[name])

    predictions: list[pd.DataFrame] = []
    coefficient_rows: list[dict] = []
    for season in TARGET_SEASONS:
        train = work[work["season"] < season].copy()
        test = work[work["season"] == season].copy()
        if test.empty:
            raise RuntimeError(f"component reconstruction missing target season {season}")
        if len(train) < 300 or train["home_win"].nunique() < 2:
            raise RuntimeError(f"insufficient component training history for {season}: {len(train)}")

        model = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=3000)
        model.fit(train[feature_cols], train["home_win"].astype(int))
        probability = model.predict_proba(test[feature_cols])[:, 1]

        part = test[["game_id", "season", "home_win", "market_prob", *COMPONENTS]].copy()
        part["component_prob"] = np.clip(probability, EPS, 1.0 - EPS)
        part["component_training_games"] = int(len(train))
        part["component_training_last_season"] = int(train["season"].max())
        predictions.append(part)

        coefficients = {
            "season": int(season),
            "training_games": int(len(train)),
            "intercept": float(model.intercept_[0]),
            "C": 1.0,
        }
        for idx, feature in enumerate(feature_cols):
            coefficients[f"coef_{feature}"] = float(model.coef_[0, idx])
        coefficient_rows.append(coefficients)

    output = pd.concat(predictions, ignore_index=True)
    output.attrs["coefficients"] = coefficient_rows
    output["component_pick"] = output["component_prob"].ge(0.5).astype(int)
    output["component_correct"] = output["component_pick"].eq(output["home_win"]).astype(int)
    return output.sort_values(["season", "game_id"], kind="stable").reset_index(drop=True)


def verify_registered_component_result(component: pd.DataFrame) -> dict:
    """Fail closed unless the registered 2022-2025 component result reproduces."""
    if len(component) != 1087:
        raise RuntimeError(f"component sample drift: {len(component)} != 1087")
    correct = int(component["component_correct"].sum())
    if correct != 744:
        raise RuntimeError(f"component challenger reproduction drift: {correct} != 744")
    return {
        "games": int(len(component)),
        "correct": correct,
        "accuracy": float(correct / len(component)),
        "brier": float(np.mean((component["component_prob"] - component["home_win"]) ** 2)),
        "registered_correct": 744,
        "registered_accuracy": 0.6844526218951242,
        "reproduced": True,
    }


def _prepare_team_state(path: str | Path) -> pd.DataFrame:
    state = pd.read_csv(path).copy()
    required = {
        "game_id", "season", "week", "team", "state_missing", "qb1_id",
        "qb1_changed", "ol_rank1_new_count", "rank1_gsis_coverage",
        "snapshot_utc", "decision_utc",
    }
    missing = required - set(state.columns)
    if missing:
        raise ValueError(f"depth-state artifact missing fields: {sorted(missing)}")
    state["season"] = pd.to_numeric(state["season"], errors="raise").astype(int)
    state["week"] = pd.to_numeric(state["week"], errors="raise").astype(int)
    state = state[state["season"].eq(2025)].copy()
    state["team"] = state["team"].map(_normalize_team)
    if state.duplicated(["game_id", "team"]).any():
        raise ValueError("depth-state artifact has duplicate game/team rows")
    known = state[~state["state_missing"].fillna(True).astype(bool)]
    if not known.empty:
        snapshot = pd.to_datetime(known["snapshot_utc"], utc=True, errors="coerce")
        decision = pd.to_datetime(known["decision_utc"], utc=True, errors="coerce")
        if snapshot.isna().any() or decision.isna().any() or snapshot.gt(decision).any():
            raise RuntimeError("depth-state T-120 chronology violation")
    return state


def _prepare_availability(path: str | Path) -> pd.DataFrame:
    availability = pd.read_csv(path, low_memory=False).copy()
    required = {
        "season", "week", "team", "gsis_id", "practice_status",
        "fully_qualified_practice_state", "known_by_t120",
    }
    missing = required - set(availability.columns)
    if missing:
        raise ValueError(f"availability artifact missing fields: {sorted(missing)}")
    availability["season"] = pd.to_numeric(availability["season"], errors="raise").astype(int)
    availability["week"] = pd.to_numeric(availability["week"], errors="raise").astype(int)
    availability = availability[availability["season"].eq(2025)].copy()
    availability["team"] = availability["team"].map(_normalize_team)
    availability["gsis_id"] = availability["gsis_id"].astype("string").fillna("").str.strip()
    availability["practice_status_norm"] = availability["practice_status"].map(normalize_practice_status)
    if availability.duplicated(["season", "week", "team", "gsis_id"]).any():
        raise ValueError("availability artifact has duplicate stable player-week rows")
    qualified = availability["fully_qualified_practice_state"].fillna(False).astype(bool)
    known = availability["known_by_t120"].fillna(False).astype(bool)
    if (qualified & ~known).any():
        raise RuntimeError("qualified practice row is not proven known by T-120")
    return availability


def attach_regime_features(
    prediction_frame: pd.DataFrame,
    team_state: pd.DataFrame,
    availability: pd.DataFrame,
) -> pd.DataFrame:
    """Attach preregistered PIT regime fields to an outcome-blind prediction frame."""
    if "home_win" in prediction_frame.columns:
        raise ValueError("regime feature builder must not receive target outcomes")
    required = {"game_id", "season", "week", "home_team", "away_team", "fst_prob", "component_prob"}
    missing = required - set(prediction_frame.columns)
    if missing:
        raise ValueError(f"candidate prediction frame missing fields: {sorted(missing)}")

    frame = prediction_frame.copy()
    frame["home_team"] = frame["home_team"].map(_normalize_team)
    frame["away_team"] = frame["away_team"].map(_normalize_team)

    state_cols = [
        "game_id", "team", "state_missing", "qb1_id", "qb1_changed",
        "ol_rank1_new_count", "rank1_gsis_coverage", "snapshot_utc", "decision_utc",
    ]
    for side in ("home", "away"):
        team_col = f"{side}_team"
        piece = team_state[state_cols].rename(
            columns={"team": team_col, **{
                column: f"{side}_{column}"
                for column in state_cols
                if column not in {"game_id", "team"}
            }}
        )
        frame = frame.merge(piece, on=["game_id", team_col], how="left", validate="one_to_one")

    availability_cols = [
        "season", "week", "team", "gsis_id", "practice_status_norm",
        "fully_qualified_practice_state", "known_by_t120",
    ]
    for side in ("home", "away"):
        team_col = f"{side}_team"
        qb_col = f"{side}_qb1_id"
        piece = availability[availability_cols].rename(columns={
            "team": team_col,
            "gsis_id": qb_col,
            "practice_status_norm": f"{side}_qb_practice_status",
            "fully_qualified_practice_state": f"{side}_qb_practice_qualified",
            "known_by_t120": f"{side}_qb_practice_known_by_t120",
        })
        frame[qb_col] = frame[qb_col].astype("string").fillna("").str.strip()
        frame = frame.merge(
            piece,
            on=["season", "week", team_col, qb_col],
            how="left",
            validate="many_to_one",
        )

    for side in ("home", "away"):
        frame[f"{side}_qb_change_shock"] = pd.to_numeric(
            frame[f"{side}_qb1_changed"], errors="coerce"
        ).eq(1.0)
        frame[f"{side}_ol_new_count"] = pd.to_numeric(
            frame[f"{side}_ol_rank1_new_count"], errors="coerce"
        )
        frame[f"{side}_qb_practice_qualified"] = (
            frame[f"{side}_qb_practice_qualified"].fillna(False).astype(bool)
        )
        frame[f"{side}_qb_practice_known_by_t120"] = (
            frame[f"{side}_qb_practice_known_by_t120"].fillna(False).astype(bool)
        )
        frame[f"{side}_qb_practice_status"] = (
            frame[f"{side}_qb_practice_status"].astype("string").fillna("")
        )
    return frame


def _practice_shock(status: pd.Series, qualified: pd.Series, mode: str) -> pd.Series:
    norm = status.astype("string").fillna("").str.lower()
    if mode == "dnp_only":
        allowed = norm.eq("dnp")
    elif mode == "dnp_or_limited":
        allowed = norm.isin({"dnp", "limited"})
    else:
        raise ValueError(f"unsupported practice mode: {mode}")
    return qualified.fillna(False).astype(bool) & allowed


def apply_gate(frame: pd.DataFrame, config: GateConfig = PRIMARY_CONFIG) -> pd.DataFrame:
    """Apply the frozen gate before target outcomes are attached."""
    if "home_win" in frame.columns:
        raise ValueError("gate must be applied before target outcomes are attached")
    work = frame.copy()

    work["boundary_eligible"] = (
        pd.to_numeric(work["fst_prob"], errors="raise") - 0.5
    ).abs().le(config.boundary)
    work["component_disagrees"] = (
        pd.to_numeric(work["component_prob"], errors="raise").ge(0.5)
        != pd.to_numeric(work["fst_prob"], errors="raise").ge(0.5)
    )

    qb_change = pd.Series(False, index=work.index)
    if config.include_qb_change:
        qb_change = (
            work["home_qb_change_shock"].fillna(False).astype(bool)
            | work["away_qb_change_shock"].fillna(False).astype(bool)
        )

    ol_churn = pd.Series(False, index=work.index)
    if config.include_ol_churn:
        ol_churn = (
            pd.to_numeric(work["home_ol_new_count"], errors="coerce").ge(config.ol_new_threshold)
            | pd.to_numeric(work["away_ol_new_count"], errors="coerce").ge(config.ol_new_threshold)
        )

    qb_practice = pd.Series(False, index=work.index)
    if config.include_qb_practice:
        qb_practice = (
            _practice_shock(
                work["home_qb_practice_status"],
                work["home_qb_practice_qualified"],
                config.practice_mode,
            )
            | _practice_shock(
                work["away_qb_practice_status"],
                work["away_qb_practice_qualified"],
                config.practice_mode,
            )
        )

    work["shock_qb_change"] = qb_change
    work["shock_ol_churn"] = ol_churn
    work["shock_qb_practice"] = qb_practice
    work["strong_regime_shock"] = qb_change | ol_churn | qb_practice
    work["candidate_switch"] = (
        work["boundary_eligible"]
        & work["component_disagrees"]
        & work["strong_regime_shock"]
    )
    work["candidate_prob"] = np.where(
        work["candidate_switch"],
        pd.to_numeric(work["component_prob"], errors="raise"),
        pd.to_numeric(work["fst_prob"], errors="raise"),
    )
    work["candidate_id"] = CANDIDATE_ID

    reasons: list[str] = []
    for row in work[["shock_qb_change", "shock_ol_churn", "shock_qb_practice"]].itertuples(index=False):
        labels = []
        if bool(row.shock_qb_change):
            labels.append("qb_change")
        if bool(row.shock_ol_churn):
            labels.append("ol_discontinuity")
        if bool(row.shock_qb_practice):
            labels.append("qb_practice_degradation")
        reasons.append("|".join(labels) if labels else "none")
    work["shock_reason"] = reasons
    return work


def build_candidate_dataset(
    *,
    depth_state_path: str | Path,
    availability_path: str | Path,
) -> tuple[pd.DataFrame, dict]:
    component = build_component_challenger()
    component_audit = verify_registered_component_result(component)

    fst = load_fst_replay()
    if len(fst) != 1087:
        raise RuntimeError(f"F-ST sample drift: {len(fst)} != 1087")
    fst_correct = int(fst["fst_prob"].ge(0.5).astype(int).eq(fst["home_win"]).sum())
    if fst_correct != 741:
        raise RuntimeError(f"F-ST incumbent reproduction drift: {fst_correct} != 741")

    merged = fst.merge(
        component[["game_id", "component_prob", *COMPONENTS]],
        on="game_id",
        how="inner",
        validate="one_to_one",
    )
    if len(merged) != 1087:
        raise RuntimeError(f"F-ST/component paired sample drift: {len(merged)} != 1087")
    target = merged[merged["season"].eq(2025)].copy()
    if target.empty:
        raise RuntimeError("Candidate 2 target season 2025 is empty")

    outcomes = target[["game_id", "home_win"]].copy()
    prediction = target.drop(columns=["home_win"]).copy()
    team_state = _prepare_team_state(depth_state_path)
    availability = _prepare_availability(availability_path)
    feature_frame = attach_regime_features(prediction, team_state, availability)
    gated = apply_gate(feature_frame, PRIMARY_CONFIG)
    scored = gated.merge(outcomes, on="game_id", how="left", validate="one_to_one")

    # Mandatory unchanged controls are attached only after Candidate 2 predictions exist.
    candidate1 = run_state_filter(load_fst_replay())
    candidate1 = candidate1[candidate1["season"].eq(2025)][["game_id", "adaptive_prob"]].rename(
        columns={"adaptive_prob": "candidate1_prob"}
    )
    weekly = attach_frozen_fst(weekly_refit_predictions(load_weekly_refit_frame()))
    weekly = weekly[weekly["season"].eq(2025)][["game_id", "weekly_refit_prob"]]
    scored = scored.merge(candidate1, on="game_id", how="left", validate="one_to_one")
    scored = scored.merge(weekly, on="game_id", how="left", validate="one_to_one")

    scored["component_only_prob"] = scored["component_prob"]
    scored["boundary_component_prob"] = np.where(
        scored["boundary_eligible"] & scored["component_disagrees"],
        scored["component_prob"],
        scored["fst_prob"],
    )

    for column in (
        "candidate_prob", "fst_prob", "market_prob", "candidate1_prob",
        "weekly_refit_prob", "component_only_prob", "boundary_component_prob",
    ):
        if scored[column].isna().any():
            raise RuntimeError(f"paired Candidate 2 comparator missing values: {column}")

    coverage = {
        "candidate_id": CANDIDATE_ID,
        "target_season": 2025,
        "paired_games": int(len(scored)),
        "component_reproduction": component_audit,
        "fst_reproduction": {
            "games": int(len(fst)),
            "correct": fst_correct,
            "accuracy": float(fst_correct / len(fst)),
        },
        "depth_both_team_state_games": int(
            (
                ~scored["home_state_missing"].fillna(True).astype(bool)
                & ~scored["away_state_missing"].fillna(True).astype(bool)
            ).sum()
        ),
        "qb_change_evaluable_games": int(
            (
                pd.to_numeric(scored["home_qb1_changed"], errors="coerce").notna()
                | pd.to_numeric(scored["away_qb1_changed"], errors="coerce").notna()
            ).sum()
        ),
        "ol_change_evaluable_games": int(
            (
                pd.to_numeric(scored["home_ol_new_count"], errors="coerce").notna()
                | pd.to_numeric(scored["away_ol_new_count"], errors="coerce").notna()
            ).sum()
        ),
        "qualified_qb_practice_join_games": int(
            (
                scored["home_qb_practice_qualified"].fillna(False).astype(bool)
                | scored["away_qb_practice_qualified"].fillna(False).astype(bool)
            ).sum()
        ),
        "strong_shock_games": int(scored["strong_regime_shock"].sum()),
        "boundary_games": int(scored["boundary_eligible"].sum()),
        "component_disagreement_games": int(scored["component_disagrees"].sum()),
        "authorized_switches": int(scored["candidate_switch"].sum()),
        "rows_preserved_with_no_strong_shock": int((~scored["strong_regime_shock"]).sum()),
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
    }
    return scored.sort_values(["season", "week", "game_id"], kind="stable").reset_index(drop=True), coverage


def summarize_primary(scored: pd.DataFrame, coverage: dict) -> dict:
    y = scored["home_win"].astype(int)
    fst_correct = scored["fst_prob"].ge(0.5).astype(int).eq(y)
    candidate_correct = scored["candidate_prob"].ge(0.5).astype(int).eq(y)
    switch = scored["candidate_switch"].astype(bool)
    candidate_only = int((switch & candidate_correct & ~fst_correct).sum())
    fst_only = int((switch & fst_correct & ~candidate_correct).sum())

    return {
        "candidate_id": CANDIDATE_ID,
        "status": "historical_preregistered_candidate2_v1",
        "sample": {
            "season": 2025,
            "games": int(len(scored)),
            "reason_for_reduced_sample": "qualified equivalent T-120 regime-state evidence is 2025-only",
        },
        "config": {
            "boundary": PRIMARY_CONFIG.boundary,
            "ol_new_threshold": PRIMARY_CONFIG.ol_new_threshold,
            "practice_mode": PRIMARY_CONFIG.practice_mode,
            "component_stack": "L2 logistic C=1.0 on market + four component logits, season-forward",
        },
        "coverage": coverage,
        "results": {
            "fst_correct": int(fst_correct.sum()),
            "fst_accuracy": float(fst_correct.mean()),
            "candidate_correct": int(candidate_correct.sum()),
            "candidate_accuracy": float(candidate_correct.mean()),
            "accuracy_delta_pp": float(100.0 * (candidate_correct.mean() - fst_correct.mean())),
            "fst_brier": float(np.mean((scored["fst_prob"] - y) ** 2)),
            "candidate_brier": float(np.mean((scored["candidate_prob"] - y) ** 2)),
            "fst_log_loss": _log_loss(scored["fst_prob"], y),
            "candidate_log_loss": _log_loss(scored["candidate_prob"], y),
            "switches": int(switch.sum()),
            "candidate_only_correct": candidate_only,
            "fst_only_correct": fst_only,
            "switch_win_rate": float(candidate_only / switch.sum()) if switch.sum() else None,
            "net_correct_from_switches": int(candidate_only - fst_only),
        },
        "governance": {
            "target_outcomes_used_to_define_features_or_thresholds": 0,
            "completed_2026_outcomes_used": 0,
            "production_changed": False,
            "promotion_authorized": False,
        },
    }


def run(
    *,
    depth_state_path: str = "research_outputs/adaptive_candidate2_v1/depth/team_game_depth_state.csv",
    availability_path: str = "research_outputs/adaptive_candidate2_v1/availability/availability_2025_canonical.csv",
    output_dir: str = "research_outputs/adaptive_candidate2_v1/model",
) -> dict:
    scored, coverage = build_candidate_dataset(
        depth_state_path=depth_state_path,
        availability_path=availability_path,
    )
    report = summarize_primary(scored, coverage)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out / "scored_games.csv", index=False)
    (out / "model_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--depth-state",
        default="research_outputs/adaptive_candidate2_v1/depth/team_game_depth_state.csv",
    )
    parser.add_argument(
        "--availability",
        default="research_outputs/adaptive_candidate2_v1/availability/availability_2025_canonical.csv",
    )
    parser.add_argument("--output-dir", default="research_outputs/adaptive_candidate2_v1/model")
    args = parser.parse_args()
    run(
        depth_state_path=args.depth_state,
        availability_path=args.availability,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
