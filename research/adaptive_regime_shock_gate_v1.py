from __future__ import annotations

"""Candidate 2: point-in-time regime-change / information-shock switch gate.

Research-only. The frozen F-ST incumbent is never modified. Candidate 2 uses a
pre-registered 2025-only personnel-regime gate to decide whether an already-defined
component-resolved challenger may replace F-ST on a near-boundary game.

No completed 2026 outcome is loaded or used.
"""

from dataclasses import dataclass
import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import nflreadpy as nfl
import numpy as np
import pandas as pd
import requests
from sklearn.linear_model import LogisticRegression

from research.adaptive_residual_state_v1 import load_fst_replay
from research.depth_chart_state_v1 import build_depth_state
from nfl_forecast.availability_2025_reconstruction import (
    NFLVERSE_EXPECTED_SHA256,
    normalize_practice_status,
    normalize_team as normalize_availability_team,
    validate_nflverse_payload,
)

CANDIDATE_ID = "ADAPTIVE-REGIME-SHOCK-GATE-V1"
TARGET_SEASON = 2025
PRIMARY_BOUNDARY = 0.075
PRIMARY_OL_NEW_THRESHOLD = 2
PRIMARY_PRACTICE_DEFINITION = "DNP_only"
COMPONENTS = ("logistic", "extra_trees", "xgboost", "catboost")
COMPONENT_C = 1.0
EPS = 1e-6
TRAINING_FRAME = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
BASE_OOF = Path("challenger_outputs/fst/provenance/base_oof_keyed.csv")
INJURY_URL = "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv"
REGISTERED_COMPONENT_CORRECT_2022_2025 = 744
REGISTERED_FST_CORRECT_2025 = 179


@dataclass(frozen=True)
class GateConfig:
    boundary: float = PRIMARY_BOUNDARY
    ol_new_threshold: int = PRIMARY_OL_NEW_THRESHOLD
    practice_definition: str = PRIMARY_PRACTICE_DEFINITION


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _logit(values: Iterable[float]) -> np.ndarray:
    p = np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def build_component_resolved_replay(
    training_path: str | Path = TRAINING_FRAME,
    base_oof_path: str | Path = BASE_OOF,
) -> pd.DataFrame:
    """Rebuild the registered component-resolved L2 stack season-forward.

    This function intentionally reproduces the previously documented 2022-2025
    component result before Candidate 2 can use its 2025 directional signal.
    """
    training = pd.read_csv(training_path)
    base = pd.read_csv(base_oof_path)
    required_training = {"game_id", "season", "home_win", "market_prob"}
    required_base = {"game_id", "season", "home_win", *COMPONENTS}
    if required_training - set(training.columns):
        raise ValueError("training frame missing component-stack inputs")
    if required_base - set(base.columns):
        raise ValueError("base OOF frame missing component probabilities")

    training = training[list(required_training)].copy()
    base = base[list(required_base)].copy()
    merged = training.merge(
        base,
        on="game_id",
        how="inner",
        suffixes=("_training", "_base"),
        validate="one_to_one",
    )
    season_training = pd.to_numeric(merged["season_training"], errors="raise").astype(int)
    season_base = pd.to_numeric(merged["season_base"], errors="raise").astype(int)
    y_training = pd.to_numeric(merged["home_win_training"], errors="raise").astype(int)
    y_base = pd.to_numeric(merged["home_win_base"], errors="raise").astype(int)
    if not season_training.equals(season_base):
        raise RuntimeError("component OOF season identity disagrees with F-ST training frame")
    if not y_training.equals(y_base):
        raise RuntimeError("component OOF outcomes disagree with F-ST training frame")

    merged["season"] = season_training
    merged["home_win"] = y_training
    merged["market_logit"] = _logit(merged["market_prob"])
    feature_cols = ["market_logit"]
    for name in COMPONENTS:
        col = f"{name}_logit"
        merged[col] = _logit(merged[name])
        feature_cols.append(col)

    predictions: list[pd.DataFrame] = []
    coefficient_rows: list[dict] = []
    for season in (2022, 2023, 2024, 2025):
        train = merged[merged["season"] < season].copy()
        test = merged[merged["season"] == season].copy()
        if test.empty:
            raise RuntimeError(f"component replay has no target rows for {season}")
        if len(train) < 300 or train["home_win"].nunique() < 2:
            raise RuntimeError(f"insufficient component training history for {season}: {len(train)}")
        model = LogisticRegression(C=COMPONENT_C, penalty="l2", solver="lbfgs", max_iter=3000)
        model.fit(train[feature_cols], train["home_win"])
        p = np.clip(model.predict_proba(test[feature_cols])[:, 1], EPS, 1.0 - EPS)
        part = test[["game_id", "season", "home_win", "market_prob", *COMPONENTS]].copy()
        part["component_prob"] = p
        predictions.append(part)
        coefficient_rows.append(
            {
                "season": season,
                "training_games": int(len(train)),
                "training_last_season": int(train["season"].max()),
                "intercept": float(model.intercept_[0]),
                **{
                    f"coef_{name}": float(value)
                    for name, value in zip(feature_cols, model.coef_[0], strict=True)
                },
            }
        )

    scored = pd.concat(predictions, ignore_index=True).sort_values("game_id", kind="stable")
    correct = int(
        (scored["component_prob"].ge(0.5).astype(int) == scored["home_win"].astype(int)).sum()
    )
    if correct != REGISTERED_COMPONENT_CORRECT_2022_2025:
        raise RuntimeError(
            f"registered component replay drift: {correct} != {REGISTERED_COMPONENT_CORRECT_2022_2025}"
        )
    scored.attrs["coefficients"] = coefficient_rows
    return scored.reset_index(drop=True)


def load_qualified_practice_state(url: str = INJURY_URL) -> tuple[pd.DataFrame, dict]:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    payload = response.content
    digest = hashlib.sha256(payload).hexdigest()
    if digest != NFLVERSE_EXPECTED_SHA256:
        raise RuntimeError(
            f"qualified 2025 injury asset drift: {digest} != {NFLVERSE_EXPECTED_SHA256}"
        )
    frame = validate_nflverse_payload(payload).copy()
    frame["week"] = pd.to_numeric(frame["week"], errors="raise").astype(int)
    frame["team"] = frame["team"].map(normalize_availability_team)
    frame["gsis_id"] = frame["gsis_id"].astype(str).str.strip()
    frame["practice_status_norm"] = frame["practice_status"].map(normalize_practice_status)

    rows: list[dict] = []
    ambiguous = 0
    for (week, team, gsis_id), part in frame.groupby(["week", "team", "gsis_id"], sort=False):
        values = sorted(
            {
                str(value)
                for value in part["practice_status_norm"].dropna().astype(str)
                if str(value).strip()
            }
        )
        if len(values) > 1:
            ambiguous += 1
            status = None
        else:
            status = values[0] if values else None
        rows.append(
            {
                "week": int(week),
                "team": str(team),
                "qb1_id": str(gsis_id),
                "qb_practice_status": status,
                "practice_join_ambiguous": len(values) > 1,
            }
        )
    compact = pd.DataFrame(rows)
    audit = {
        "source": url,
        "sha256": digest,
        "rows": int(len(frame)),
        "unique_player_week_keys": int(len(compact)),
        "ambiguous_player_week_status_keys": int(ambiguous),
        "historical_game_status_used": False,
        "postgame_participation_used": 0,
        "actual_snaps_used": 0,
        "completed_2026_outcomes_used": 0,
    }
    return compact, audit


def build_2025_personnel_state() -> tuple[pd.DataFrame, dict]:
    depth = _pandas(nfl.load_depth_charts([TARGET_SEASON]))
    schedules = _pandas(nfl.load_schedules([TARGET_SEASON]))
    keep = [
        c
        for c in [
            "game_id",
            "season",
            "week",
            "game_type",
            "gameday",
            "gametime",
            "home_team",
            "away_team",
        ]
        if c in schedules.columns
    ]
    schedules = schedules[keep].copy()
    if "game_type" in schedules.columns:
        schedules = schedules[schedules["game_type"].astype(str).isin({"REG", "POST"})].copy()
    schedules = schedules[
        schedules["game_id"].notna()
        & schedules["home_team"].notna()
        & schedules["away_team"].notna()
    ].copy()
    built = build_depth_state(depth, schedules)
    practice, practice_audit = load_qualified_practice_state()

    team = built.team_game_state.copy()
    team["qb1_id"] = team["qb1_id"].astype("string")
    joined = team.merge(
        practice,
        on=["week", "team", "qb1_id"],
        how="left",
        validate="many_to_one",
    )
    conflict = joined["practice_join_ambiguous"].fillna(False).astype(bool)
    if conflict.any():
        examples = joined.loc[conflict, ["game_id", "team", "qb1_id"]].head().to_dict("records")
        raise RuntimeError(f"ambiguous stable-ID QB practice join: {examples}")

    audit = {
        "depth": built.audit,
        "practice": practice_audit,
        "team_games": int(len(joined)),
        "team_games_with_depth_state": int((~joined["state_missing"].astype(bool)).sum()),
        "team_games_with_qb1": int(joined["qb1_id"].notna().sum()),
        "team_games_with_qb_practice_row": int(joined["qb_practice_status"].notna().sum()),
        "future_snapshot_violations": int(built.audit["future_snapshot_violations"]),
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
    }
    if audit["future_snapshot_violations"] != 0:
        raise RuntimeError("future depth-chart snapshot detected")
    return joined, audit


def attach_personnel_channels(base: pd.DataFrame, team_state: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    keep = [
        "game_id",
        "team",
        "state_missing",
        "rank1_gsis_coverage",
        "qb1_changed",
        "ol_rank1_new_count",
        "offense_rank1_new_count",
        "defense_rank1_new_count",
        "qb_practice_status",
    ]
    for side in ("home", "away"):
        team_col = f"{side}_team"
        piece = team_state[keep].rename(
            columns={
                "team": team_col,
                **{
                    c: f"{side}_{c}"
                    for c in keep
                    if c not in {"game_id", "team"}
                },
            }
        )
        out = out.merge(piece, on=["game_id", team_col], how="left", validate="one_to_one")
    return out


def _practice_shock(series: pd.Series, definition: str) -> pd.Series:
    status = series.astype("string").fillna("").str.lower().str.strip()
    if definition == "DNP_only":
        return status.eq("dnp")
    if definition == "DNP_or_limited":
        return status.isin({"dnp", "limited"})
    raise ValueError(f"unknown practice definition: {definition}")


def apply_gate(frame: pd.DataFrame, config: GateConfig = GateConfig()) -> pd.DataFrame:
    """Apply the frozen gate without reading target outcomes."""
    required = {
        "game_id",
        "fst_prob",
        "component_prob",
        "home_qb1_changed",
        "away_qb1_changed",
        "home_ol_rank1_new_count",
        "away_ol_rank1_new_count",
        "home_qb_practice_status",
        "away_qb_practice_status",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Candidate 2 gate missing fields: {sorted(missing)}")

    out = frame.copy()
    fst_side = out["fst_prob"].ge(0.5)
    component_side = out["component_prob"].ge(0.5)
    out["boundary_eligible"] = out["fst_prob"].sub(0.5).abs().le(config.boundary)
    out["component_disagrees"] = fst_side.ne(component_side)

    home_qb_change = pd.to_numeric(out["home_qb1_changed"], errors="coerce").eq(1.0)
    away_qb_change = pd.to_numeric(out["away_qb1_changed"], errors="coerce").eq(1.0)
    out["shock_qb_change"] = home_qb_change | away_qb_change

    home_ol = pd.to_numeric(out["home_ol_rank1_new_count"], errors="coerce")
    away_ol = pd.to_numeric(out["away_ol_rank1_new_count"], errors="coerce")
    out["shock_ol_churn"] = home_ol.ge(config.ol_new_threshold) | away_ol.ge(
        config.ol_new_threshold
    )
    out["shock_qb_practice"] = _practice_shock(
        out["home_qb_practice_status"], config.practice_definition
    ) | _practice_shock(out["away_qb_practice_status"], config.practice_definition)

    out["strong_regime_shock"] = (
        out["shock_qb_change"] | out["shock_ol_churn"] | out["shock_qb_practice"]
    )
    out["candidate_switch"] = (
        out["boundary_eligible"] & out["component_disagrees"] & out["strong_regime_shock"]
    )
    out["candidate_prob"] = np.where(
        out["candidate_switch"], out["component_prob"], out["fst_prob"]
    )
    out["candidate_id"] = CANDIDATE_ID
    out["candidate_boundary"] = float(config.boundary)
    out["candidate_ol_new_threshold"] = int(config.ol_new_threshold)
    out["candidate_practice_definition"] = str(config.practice_definition)

    def reason(row: pd.Series) -> str:
        if not bool(row["candidate_switch"]):
            return "preserve_fst"
        channels = []
        if bool(row["shock_qb_change"]):
            channels.append("qb_change")
        if bool(row["shock_ol_churn"]):
            channels.append("ol_churn")
        if bool(row["shock_qb_practice"]):
            channels.append("qb_practice")
        return "+".join(channels)

    out["switch_reason"] = out.apply(reason, axis=1)
    return out


def build_candidate_frame() -> tuple[pd.DataFrame, dict]:
    fst = load_fst_replay()
    fst = fst[fst["season"].eq(TARGET_SEASON)].copy()
    fst_correct = int(
        (fst["fst_prob"].ge(0.5).astype(int) == fst["home_win"].astype(int)).sum()
    )
    if fst_correct != REGISTERED_FST_CORRECT_2025:
        raise RuntimeError(
            f"2025 F-ST reproduction drift: {fst_correct} != {REGISTERED_FST_CORRECT_2025}"
        )

    components_all = build_component_resolved_replay()
    component_coefficients = components_all.attrs.get("coefficients", [])
    components = components_all[components_all["season"].eq(TARGET_SEASON)][
        ["game_id", "component_prob"]
    ].copy()
    base = fst.merge(components, on="game_id", how="inner", validate="one_to_one")
    if len(base) != len(fst):
        raise RuntimeError(f"component/F-ST 2025 row mismatch: {len(base)} != {len(fst)}")

    team_state, personnel_audit = build_2025_personnel_state()
    enriched = attach_personnel_channels(base, team_state)
    scored = apply_gate(enriched, GateConfig())
    audit = {
        "candidate_id": CANDIDATE_ID,
        "target_season": TARGET_SEASON,
        "paired_games": int(len(scored)),
        "fst_correct_reproduced": fst_correct,
        "registered_component_full_sample_correct_reproduced": REGISTERED_COMPONENT_CORRECT_2022_2025,
        "component_coefficients": component_coefficients,
        "personnel": personnel_audit,
        "coverage": {
            "both_team_depth_state": int(
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
                    pd.to_numeric(scored["home_ol_rank1_new_count"], errors="coerce").notna()
                    | pd.to_numeric(scored["away_ol_rank1_new_count"], errors="coerce").notna()
                ).sum()
            ),
            "qb_practice_join_games": int(
                (
                    scored["home_qb_practice_status"].notna()
                    | scored["away_qb_practice_status"].notna()
                ).sum()
            ),
            "strong_shock_games": int(scored["strong_regime_shock"].sum()),
            "boundary_component_disagreement_games": int(
                (scored["boundary_eligible"] & scored["component_disagrees"]).sum()
            ),
            "authorized_switches": int(scored["candidate_switch"].sum()),
        },
        "governance": {
            "completed_2026_outcomes_used": 0,
            "post_t120_state_used": False,
            "closing_line_used": False,
            "production_changed": False,
            "promotion_authorized": False,
        },
    }
    return scored, audit


def run(output_dir: str = "research_outputs/adaptive_candidate2_v1") -> dict:
    scored, audit = build_candidate_frame()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out / "scored_games.csv", index=False)
    (out / "construction_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True, default=str))
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/adaptive_candidate2_v1")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
