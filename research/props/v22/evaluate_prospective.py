from __future__ import annotations

"""Prospective evaluator for the frozen LevLine Props 2.2 challenger grid.

Research-only. This module never mutates prospective receipts, never fits challenger
coefficients, and never promotes a winner automatically. It joins immutable Props 2.2
receipts to separately supplied finalized grades and reports the metrics preregistered
before the future holdout.
"""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import numpy as np
import pandas as pd

from research.props.v22.challengers import load_grid


EVALUATION_CONTRACT_VERSION = "levline-props-2.2-eval-v0.1"
GRADE_CONTRACT_VERSION = "levline-props-2.2-grade-v0.1"
RECEIPT_CONTRACT_VERSION = "levline-props-2.2-prereg-v0.2"
BOOTSTRAP_SEED = 20260922
BOOTSTRAP_REPLICATES = 5000
PROB_EPS = 1e-12
LINE_MARKETS = frozenset(
    {"passing_yards", "rushing_yards", "receiving_yards", "receptions", "passing_tds"}
)
BINARY_TD_MARKETS = frozenset({"rushing_td", "receiving_td", "anytime_td"})
FIXED_CALIBRATION_BINS = (
    (0.50, 0.55, "50-55%"),
    (0.55, 0.60, "55-60%"),
    (0.60, 0.65, "60-65%"),
    (0.65, 0.70, "65-70%"),
    (0.70, 1.0000000001, "70%+"),
)


class Props22EvaluationError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _num(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _prob(value: Any) -> float | None:
    result = _num(value)
    if result is None or not 0.0 <= result <= 1.0:
        return None
    return result


def _timestamp(value: Any) -> pd.Timestamp | None:
    if value in (None, ""):
        return None
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _week_key(game_id: Any) -> str | None:
    parts = str(game_id or "").split("_")
    if len(parts) < 2:
        return None
    try:
        return f"{int(parts[0]):04d}_{int(parts[1]):02d}"
    except ValueError:
        return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Props22EvaluationError(f"{path}:{line_no}: invalid JSON") from exc
            if not isinstance(value, dict):
                raise Props22EvaluationError(f"{path}:{line_no}: row must be a JSON object")
            rows.append(value)
    return rows


def validate_receipts(
    rows: Iterable[Mapping[str, Any]],
    *,
    grid: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    frozen = dict(grid or load_grid())
    expected_ids = {
        str(item.get("id"))
        for item in frozen.get("challengers") or []
        if isinstance(item, Mapping)
    }
    baseline = str(frozen.get("baseline_model") or "")
    seen: dict[tuple[str, str], str] = {}
    out: list[dict[str, Any]] = []

    for raw in rows:
        row = dict(raw)
        if row.get("contract_version") != RECEIPT_CONTRACT_VERSION:
            raise Props22EvaluationError("unexpected Props 2.2 receipt contract")
        if row.get("research_only") is not True or row.get("production_authorized") is not False:
            raise Props22EvaluationError("Props 2.2 receipt violates research-only governance")
        if row.get("outcome") is not None:
            raise Props22EvaluationError("prospective Props 2.2 receipt contains an outcome")

        challenger_id = str(row.get("challenger_id") or "")
        if challenger_id not in expected_ids:
            raise Props22EvaluationError(f"unknown/frozen-grid challenger id: {challenger_id!r}")
        if str(row.get("source_props21_model_version") or "") != baseline:
            raise Props22EvaluationError("Props 2.2 receipt baseline model identity mismatch")

        source_sha = str(row.get("source_props21_forecast_sha256") or "")
        source_id = str(row.get("source_props21_forecast_id") or "")
        receipt_sha = str(row.get("receipt_sha256") or "")
        if len(source_sha) != 64 or not source_id or len(receipt_sha) != 64:
            raise Props22EvaluationError("Props 2.2 receipt is missing immutable identity hashes")
        unhashed = dict(row)
        unhashed.pop("receipt_sha256", None)
        if _sha(unhashed) != receipt_sha:
            raise Props22EvaluationError("Props 2.2 receipt hash mismatch")

        chronology = row.get("chronology")
        if not isinstance(chronology, Mapping) or chronology.get("source_chronology_ok") is not True:
            raise Props22EvaluationError("Props 2.2 source chronology is invalid")
        forecast_at = _timestamp(row.get("forecast_timestamp_utc"))
        kickoff_at = _timestamp(row.get("kickoff_utc"))
        horizon_at = _timestamp(row.get("source_data_horizon_utc"))
        if None in {forecast_at, kickoff_at, horizon_at} or not (horizon_at <= forecast_at < kickoff_at):
            raise Props22EvaluationError("Props 2.2 timestamp chronology is invalid")

        line = row.get("line") if isinstance(row.get("line"), Mapping) else {}
        probability = (
            row.get("probability") if isinstance(row.get("probability"), Mapping) else {}
        )
        market_required = (
            float(line.get("market_weight") or 0.0) > 0.0
            or float(probability.get("market_weight") or 0.0) > 0.0
        )
        if market_required and chronology.get("market_chronology_ok") is not True:
            raise Props22EvaluationError(
                f"{challenger_id}: market-anchored receipt has invalid market chronology"
            )

        identity = (source_sha, challenger_id)
        prior = seen.get(identity)
        if prior is not None and prior != receipt_sha:
            raise Props22EvaluationError(f"conflicting duplicate challenger receipt: {identity}")
        if prior is not None:
            continue
        seen[identity] = receipt_sha
        out.append(row)
    return out


def validate_grades(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grades: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        if row.get("contract_version") != GRADE_CONTRACT_VERSION:
            raise Props22EvaluationError("unexpected Props 2.2 grade contract")
        source_sha = str(row.get("source_props21_forecast_sha256") or "")
        source_id = str(row.get("source_props21_forecast_id") or "")
        game_id = str(row.get("game_id") or "")
        status = str(row.get("grade_status") or "").upper()
        if len(source_sha) != 64 or not source_id or not game_id:
            raise Props22EvaluationError("grade is missing source identity")
        if status not in {"GRADED", "VOID"}:
            raise Props22EvaluationError(f"unsupported grade status: {status!r}")
        if row.get("finalized") is not True:
            raise Props22EvaluationError("Props 2.2 evaluator accepts finalized grades only")
        graded_at = _timestamp(row.get("graded_utc"))
        if graded_at is None:
            raise Props22EvaluationError("grade is missing a timezone-aware graded_utc")
        actual = _num(row.get("actual_result"))
        if status == "GRADED" and actual is None:
            raise Props22EvaluationError("graded row is missing numeric actual_result")
        if status == "VOID" and row.get("actual_result") is not None:
            raise Props22EvaluationError("void row may not contain actual_result")
        prior = grades.get(source_sha)
        if prior is not None and _canonical(prior) != _canonical(row):
            raise Props22EvaluationError(f"conflicting duplicate grade for {source_sha}")
        grades[source_sha] = row
    return grades


def join_receipts_and_grades(
    receipts: Iterable[Mapping[str, Any]],
    grades: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for receipt in receipts:
        source_sha = str(receipt["source_props21_forecast_sha256"])
        grade = grades.get(source_sha)
        if not grade or str(grade.get("grade_status") or "").upper() != "GRADED":
            continue
        if str(grade.get("source_props21_forecast_id")) != str(
            receipt.get("source_props21_forecast_id")
        ):
            raise Props22EvaluationError("grade/receipt source forecast id mismatch")
        if str(grade.get("game_id")) != str(receipt.get("game_id")):
            raise Props22EvaluationError("grade/receipt game id mismatch")
        graded_at = _timestamp(grade.get("graded_utc"))
        kickoff_at = _timestamp(receipt.get("kickoff_utc"))
        if graded_at is None or kickoff_at is None or graded_at < kickoff_at:
            raise Props22EvaluationError("grade timestamp precedes kickoff")

        line = receipt.get("line") or {}
        probability = receipt.get("probability") or {}
        role = receipt.get("role_state") or {}
        market_state = receipt.get("market_state") or {}
        rows.append(
            {
                "source_sha": source_sha,
                "source_forecast_id": receipt.get("source_props21_forecast_id"),
                "challenger_id": receipt.get("challenger_id"),
                "challenger_role": receipt.get("challenger_role"),
                "promotion_eligible": bool(receipt.get("promotion_eligible")),
                "game_id": receipt.get("game_id"),
                "week_key": _week_key(receipt.get("game_id")),
                "player_id": receipt.get("player_id"),
                "position": receipt.get("position"),
                "prop_type": receipt.get("prop_type"),
                "actual_result": float(grade["actual_result"]),
                "market_line": _num(line.get("market_line")),
                "model_fair_line": _num(line.get("model_fair_line")),
                "challenger_line": _num(line.get("challenger_line")),
                "line_available": bool(line.get("line_available")),
                "model_line_residual": _num(line.get("model_residual_vs_market")),
                "probability_kind": probability.get("kind"),
                "market_probability": _prob(probability.get("market_probability")),
                "model_probability": _prob(probability.get("model_probability")),
                "challenger_probability": _prob(
                    probability.get("challenger_probability")
                ),
                "probability_available": bool(
                    probability.get("probability_available")
                ),
                "role_state": role.get("state") if isinstance(role, Mapping) else None,
                "availability_state": (
                    role.get("availability") if isinstance(role, Mapping) else None
                ),
                "workload_state": (
                    role.get("workload") if isinstance(role, Mapping) else None
                ),
                "book_count": (
                    market_state.get("book_count")
                    if isinstance(market_state, Mapping)
                    else None
                ),
            }
        )
    return pd.DataFrame(rows)


def _cluster_bootstrap(
    frame: pd.DataFrame,
    statistic: Callable[[pd.DataFrame], float],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float | None, float | None]:
    if frame.empty or "game_id" not in frame:
        return None, None
    games = sorted(frame["game_id"].dropna().astype(str).unique())
    if not games:
        return None, None
    rng = np.random.default_rng(seed)
    values: list[float] = []
    groups = {game: frame[frame["game_id"].astype(str).eq(game)] for game in games}
    for _ in range(max(1, int(replicates))):
        chosen = rng.choice(games, size=len(games), replace=True)
        sample = pd.concat([groups[str(game)] for game in chosen], ignore_index=True)
        value = float(statistic(sample))
        if math.isfinite(value):
            values.append(value)
    if not values:
        return None, None
    lo, hi = np.quantile(np.asarray(values), [0.025, 0.975])
    return float(lo), float(hi)


def _cluster_sign_flip_pvalue(
    frame: pd.DataFrame,
    difference_column: str,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> float | None:
    work = frame[["game_id", difference_column]].dropna().copy()
    if work.empty:
        return None
    cluster_sums = (
        work.groupby("game_id", sort=True)[difference_column].sum().astype(float).to_numpy()
    )
    if len(cluster_sums) < 2:
        return None
    observed = abs(float(cluster_sums.sum() / len(work)))
    rng = np.random.default_rng(seed)
    exceed = 0
    total = max(1, int(replicates))
    for _ in range(total):
        signs = rng.choice(np.asarray([-1.0, 1.0]), size=len(cluster_sums))
        permuted = abs(float(np.sum(cluster_sums * signs) / len(work)))
        exceed += int(permuted >= observed - 1e-15)
    return float((exceed + 1) / (total + 1))


def holm_bonferroni(pvalues: Mapping[str, float | None]) -> dict[str, float | None]:
    valid = sorted(
        ((key, float(value)) for key, value in pvalues.items() if value is not None),
        key=lambda item: item[1],
    )
    adjusted: dict[str, float | None] = {key: None for key in pvalues}
    running = 0.0
    m = len(valid)
    for rank, (key, value) in enumerate(valid):
        candidate = min(1.0, (m - rank) * value)
        running = max(running, candidate)
        adjusted[key] = running
    return adjusted


def _line_metrics(
    frame: pd.DataFrame,
    *,
    bootstrap_replicates: int,
) -> dict[str, Any]:
    work = frame[
        frame["prop_type"].isin(LINE_MARKETS)
        & frame["line_available"]
        & frame["challenger_line"].notna()
        & frame["market_line"].notna()
        & frame["actual_result"].notna()
    ].copy()
    if work.empty:
        return {"n": 0, "unique_games": 0, "status": "NO_MATCHED_LINE_OBSERVATIONS"}
    work["challenger_abs_error"] = np.abs(
        work["challenger_line"].astype(float) - work["actual_result"].astype(float)
    )
    work["market_abs_error"] = np.abs(
        work["market_line"].astype(float) - work["actual_result"].astype(float)
    )
    work["paired_difference"] = (
        work["challenger_abs_error"] - work["market_abs_error"]
    )
    ci = _cluster_bootstrap(
        work,
        lambda x: float(x["paired_difference"].mean()),
        replicates=bootstrap_replicates,
    )
    return {
        "n": int(len(work)),
        "unique_games": int(work["game_id"].nunique()),
        "unique_weeks": int(work["week_key"].dropna().nunique()),
        "mae_challenger": float(work["challenger_abs_error"].mean()),
        "mae_original_market": float(work["market_abs_error"].mean()),
        "paired_absolute_error_difference_challenger_minus_market": float(
            work["paired_difference"].mean()
        ),
        "paired_difference_ci95_game_clustered": list(ci),
        "paired_difference_sign_flip_pvalue_game_clustered": _cluster_sign_flip_pvalue(
            work,
            "paired_difference",
            replicates=bootstrap_replicates,
        ),
        "status": "DESCRIPTIVE",
    }


def _probability_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        challenger_p = _prob(row.get("challenger_probability"))
        market_p = _prob(row.get("market_probability"))
        if (
            not bool(row.get("probability_available"))
            or challenger_p is None
            or market_p is None
        ):
            continue
        prop = str(row.get("prop_type") or "")
        actual = _num(row.get("actual_result"))
        if actual is None:
            continue
        if prop in LINE_MARKETS:
            line = _num(row.get("market_line"))
            if line is None or actual == line:
                continue
            observed = 1.0 if actual > line else 0.0
        elif prop in BINARY_TD_MARKETS:
            observed = 1.0 if actual >= 1.0 else 0.0
        else:
            continue
        favored_p = challenger_p if challenger_p >= 0.5 else 1.0 - challenger_p
        favored_y = observed if challenger_p >= 0.5 else 1.0 - observed
        rows.append(
            {
                **row.to_dict(),
                "event_observed": observed,
                "favored_probability": favored_p,
                "favored_observed": favored_y,
            }
        )
    return pd.DataFrame(rows)


def _log_loss(probability: pd.Series, observed: pd.Series) -> pd.Series:
    p = np.clip(probability.astype(float).to_numpy(), PROB_EPS, 1.0 - PROB_EPS)
    y = observed.astype(float).to_numpy()
    return pd.Series(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _calibration(work: pd.DataFrame) -> tuple[list[dict[str, Any]], float | None]:
    if work.empty:
        return [], None
    rows: list[dict[str, Any]] = []
    weighted_gap = 0.0
    total = 0
    for low, high, label in FIXED_CALIBRATION_BINS:
        bucket = work[
            work["favored_probability"].ge(low) & work["favored_probability"].lt(high)
        ]
        n = len(bucket)
        if not n:
            rows.append(
                {
                    "bin": label,
                    "n": 0,
                    "unique_games": 0,
                    "mean_predicted_probability": None,
                    "observed_frequency": None,
                    "calibration_gap": None,
                }
            )
            continue
        predicted = float(bucket["favored_probability"].mean())
        observed = float(bucket["favored_observed"].mean())
        gap = observed - predicted
        weighted_gap += n * abs(gap)
        total += n
        rows.append(
            {
                "bin": label,
                "n": n,
                "unique_games": int(bucket["game_id"].nunique()),
                "mean_predicted_probability": predicted,
                "observed_frequency": observed,
                "calibration_gap": gap,
            }
        )
    return rows, float(weighted_gap / total) if total else None


def _probability_metrics(
    frame: pd.DataFrame,
    *,
    bootstrap_replicates: int,
) -> dict[str, Any]:
    work = _probability_frame(frame)
    if work.empty:
        return {
            "n": 0,
            "unique_games": 0,
            "status": "NO_MATCHED_PROBABILITY_OBSERVATIONS",
            "calibration": [],
        }
    work["challenger_brier"] = np.square(
        work["challenger_probability"].astype(float) - work["event_observed"].astype(float)
    )
    work["market_brier"] = np.square(
        work["market_probability"].astype(float) - work["event_observed"].astype(float)
    )
    work["brier_difference"] = work["challenger_brier"] - work["market_brier"]
    work["challenger_log_loss"] = _log_loss(
        work["challenger_probability"], work["event_observed"]
    ).to_numpy()
    work["market_log_loss"] = _log_loss(
        work["market_probability"], work["event_observed"]
    ).to_numpy()
    work["log_loss_difference"] = (
        work["challenger_log_loss"] - work["market_log_loss"]
    )
    brier_ci = _cluster_bootstrap(
        work,
        lambda x: float(x["brier_difference"].mean()),
        replicates=bootstrap_replicates,
    )
    log_ci = _cluster_bootstrap(
        work,
        lambda x: float(x["log_loss_difference"].mean()),
        replicates=bootstrap_replicates,
    )
    calibration, ece = _calibration(work)
    return {
        "n": int(len(work)),
        "unique_games": int(work["game_id"].nunique()),
        "unique_weeks": int(work["week_key"].dropna().nunique()),
        "brier_challenger": float(work["challenger_brier"].mean()),
        "brier_original_market": float(work["market_brier"].mean()),
        "brier_difference_challenger_minus_market": float(
            work["brier_difference"].mean()
        ),
        "brier_difference_ci95_game_clustered": list(brier_ci),
        "brier_sign_flip_pvalue_game_clustered": _cluster_sign_flip_pvalue(
            work, "brier_difference", replicates=bootstrap_replicates
        ),
        "log_loss_challenger": float(work["challenger_log_loss"].mean()),
        "log_loss_original_market": float(work["market_log_loss"].mean()),
        "log_loss_difference_challenger_minus_market": float(
            work["log_loss_difference"].mean()
        ),
        "log_loss_difference_ci95_game_clustered": list(log_ci),
        "log_loss_sign_flip_pvalue_game_clustered": _cluster_sign_flip_pvalue(
            work, "log_loss_difference", replicates=bootstrap_replicates
        ),
        "calibration": calibration,
        "expected_calibration_error": ece,
        "status": "DESCRIPTIVE",
    }


def _residual_metrics(
    frame: pd.DataFrame,
    *,
    bootstrap_replicates: int,
) -> dict[str, Any]:
    work = frame[
        frame["prop_type"].isin(LINE_MARKETS)
        & frame["market_line"].notna()
        & frame["model_line_residual"].notna()
        & frame["actual_result"].notna()
    ].copy()
    if work.empty:
        return {"n": 0, "status": "NO_MATCHED_RESIDUAL_OBSERVATIONS"}
    work["x"] = work["model_line_residual"].astype(float)
    work["y"] = work["actual_result"].astype(float) - work["market_line"].astype(float)

    def slope(sample: pd.DataFrame) -> float:
        x = sample["x"].astype(float).to_numpy()
        y = sample["y"].astype(float).to_numpy()
        centered = x - x.mean()
        denom = float(np.square(centered).sum())
        if denom <= 0:
            return float("nan")
        return float(np.sum(centered * (y - y.mean())) / denom)

    observed_slope = slope(work)
    slope_ci = _cluster_bootstrap(
        work, slope, replicates=bootstrap_replicates
    )
    nonzero = work[work["x"].ne(0) & work["y"].ne(0)]
    sign_agreement = (
        float(np.mean(np.sign(nonzero["x"]) == np.sign(nonzero["y"])))
        if not nonzero.empty
        else None
    )
    return {
        "n": int(len(work)),
        "unique_games": int(work["game_id"].nunique()),
        "market_residual_slope": observed_slope if math.isfinite(observed_slope) else None,
        "market_residual_slope_ci95_game_clustered": list(slope_ci),
        "residual_sign_agreement": sign_agreement,
        "pearson_correlation": (
            float(work["x"].corr(work["y"], method="pearson")) if len(work) >= 2 else None
        ),
        "spearman_correlation": (
            float(work["x"].corr(work["y"], method="spearman")) if len(work) >= 2 else None
        ),
        "status": "DESCRIPTIVE",
    }


def _candidate_readiness(frame: pd.DataFrame, minimums: Mapping[str, Any]) -> dict[str, Any]:
    sources = frame.drop_duplicates("source_sha") if not frame.empty else frame
    weeks = int(sources["week_key"].dropna().nunique()) if not sources.empty else 0
    games = int(sources["game_id"].dropna().nunique()) if not sources.empty else 0
    market_matched = int(
        (
            sources["market_line"].notna()
            | sources["market_probability"].notna()
        ).sum()
    ) if not sources.empty else 0
    family_counts = (
        sources.groupby("prop_type")["source_sha"].nunique().astype(int).to_dict()
        if not sources.empty
        else {}
    )
    ready = (
        weeks >= int(minimums.get("future_weeks") or 0)
        and games >= int(minimums.get("finalized_games") or 0)
        and market_matched >= int(minimums.get("market_matched_observations") or 0)
    )
    return {
        "future_weeks": weeks,
        "finalized_games": games,
        "market_matched_observations": market_matched,
        "prop_family_observations": family_counts,
        "terminal_evaluation_ready": ready,
        "prop_family_claim_ready": {
            prop: count >= int(minimums.get("prop_family_observations") or 0)
            for prop, count in sorted(family_counts.items())
        },
    }


def evaluate(
    receipts: Iterable[Mapping[str, Any]],
    grades: Iterable[Mapping[str, Any]],
    *,
    grid: Mapping[str, Any] | None = None,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
) -> tuple[dict[str, Any], pd.DataFrame]:
    frozen = dict(grid or load_grid())
    valid_receipts = validate_receipts(receipts, grid=frozen)
    grade_map = validate_grades(grades)
    detail = join_receipts_and_grades(valid_receipts, grade_map)

    candidate_metrics: dict[str, Any] = {}
    line_pvalues: dict[str, float | None] = {}
    brier_pvalues: dict[str, float | None] = {}
    log_pvalues: dict[str, float | None] = {}
    promotion_ids = set(
        (frozen.get("selection_control") or {}).get("promotion_candidate_ids") or []
    )

    for challenger in frozen.get("challengers") or []:
        challenger_id = str(challenger.get("id"))
        candidate = detail[detail["challenger_id"].eq(challenger_id)].copy()
        line = _line_metrics(candidate, bootstrap_replicates=bootstrap_replicates)
        probability = _probability_metrics(
            candidate, bootstrap_replicates=bootstrap_replicates
        )
        residual = _residual_metrics(
            candidate, bootstrap_replicates=bootstrap_replicates
        )
        candidate_metrics[challenger_id] = {
            "role": challenger.get("role"),
            "promotion_eligible": bool(challenger.get("promotion_eligible")),
            "line": line,
            "probability": probability,
            "market_residual": residual,
        }
        if challenger_id in promotion_ids:
            line_pvalues[challenger_id] = line.get(
                "paired_difference_sign_flip_pvalue_game_clustered"
            )
            brier_pvalues[challenger_id] = probability.get(
                "brier_sign_flip_pvalue_game_clustered"
            )
            log_pvalues[challenger_id] = probability.get(
                "log_loss_sign_flip_pvalue_game_clustered"
            )

    primary_source = detail[
        detail["challenger_id"].isin(promotion_ids)
    ].drop_duplicates("source_sha")
    readiness = _candidate_readiness(
        primary_source,
        frozen.get("minimum_promotion_evidence") or {},
    )
    selection = frozen.get("selection_control") or {}
    multiplicity = {
        "method": selection.get("multiplicity_method"),
        "family_alpha": selection.get("family_alpha"),
        "line_pvalues_holm_adjusted": holm_bonferroni(line_pvalues),
        "brier_pvalues_holm_adjusted": holm_bonferroni(brier_pvalues),
        "log_loss_pvalues_holm_adjusted": holm_bonferroni(log_pvalues),
    }

    summary = {
        "evaluation_contract_version": EVALUATION_CONTRACT_VERSION,
        "preregistration_contract_version": frozen.get("contract_version"),
        "baseline_model": frozen.get("baseline_model"),
        "research_only": True,
        "production_authorized": False,
        "receipt_count": len(valid_receipts),
        "graded_source_forecasts": int(detail["source_sha"].nunique())
        if not detail.empty
        else 0,
        "candidate_metrics": candidate_metrics,
        "terminal_readiness": readiness,
        "multiplicity": multiplicity,
        "promotion_decision": (
            "TERMINAL_EVALUATION_PERMITTED_BUT_NO_AUTOMATIC_WINNER_SELECTION"
            if readiness["terminal_evaluation_ready"]
            else "NOT_READY_CONTINUE_FROZEN_HOLDOUT"
        ),
        "guardrail": (
            "Per-week results are descriptive. Candidate definitions remain frozen; "
            "this evaluator reports preregistered evidence and never auto-promotes a model."
        ),
    }
    return summary, detail


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--grades", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--detail", type=Path)
    parser.add_argument("--bootstrap-replicates", type=int, default=BOOTSTRAP_REPLICATES)
    args = parser.parse_args()

    receipts = read_jsonl(args.receipts)
    grades = read_jsonl(args.grades)
    summary, detail = evaluate(
        receipts,
        grades,
        bootstrap_replicates=args.bootstrap_replicates,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    if args.detail is not None:
        args.detail.parent.mkdir(parents=True, exist_ok=True)
        detail.to_csv(args.detail, index=False)
    print(json.dumps(summary["terminal_readiness"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
