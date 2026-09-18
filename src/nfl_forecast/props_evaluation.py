from __future__ import annotations

"""Scientific evaluation utilities for the frozen LevLine Props Research Beta.

This module is evaluation-only. It consumes immutable forecast/history events and never
changes the Props model, signal thresholds, official LevLine/F-ST winner logic, or any
prospective forecast receipt.
"""

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite, log, sqrt
from statistics import NormalDist
from typing import Any, Callable, Iterable, Mapping, Sequence
import json

import numpy as np
import pandas as pd


EVALUATION_CONTRACT_VERSION = "levline-props-eval-v1.0"
BOOTSTRAP_SEED = 20260917
BOOTSTRAP_REPLICATES = 5000
PROB_EPS = 1e-12

LINE_MARKETS = frozenset(
    {"passing_yards", "rushing_yards", "receiving_yards", "receptions", "passing_tds"}
)
BINARY_TD_MARKETS = frozenset({"rushing_td", "receiving_td", "anytime_td"})
CONTINUOUS_EVAL_MARKETS = LINE_MARKETS

FIXED_CALIBRATION_BINS = (
    (0.50, 0.55, "50-55%"),
    (0.55, 0.60, "55-60%"),
    (0.60, 0.65, "60-65%"),
    (0.65, 0.70, "65-70%"),
    (0.70, 1.0000000001, "70%+"),
)


class PropsEvaluationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SampleCounts:
    forecasts: int
    unique_players: int
    unique_games: int
    unique_weeks: int


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "null", "<na>"}:
        return None
    return text


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if isfinite(out) else None


def _prob(value: Any) -> float | None:
    out = _num(value)
    return out if out is not None and 0.0 <= out <= 1.0 else None


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def original_sha256(original: Mapping[str, Any]) -> str:
    return sha256(_canonical(original).encode("utf-8")).hexdigest()


def american_to_decimal(odds: Any) -> float | None:
    value = _num(odds)
    if value is None or (-100.0 < value < 100.0):
        return None
    return 1.0 + (100.0 / abs(value) if value < 0.0 else value / 100.0)


def _week_from_row(game_id: str | None, kickoff: Any) -> str | None:
    if game_id:
        parts = str(game_id).split("_")
        if len(parts) >= 2 and parts[1].isdigit():
            return f"{parts[0]}-W{int(parts[1]):02d}"
    ts = pd.to_datetime(kickoff, utc=True, errors="coerce")
    if pd.notna(ts):
        iso = ts.isocalendar()
        return f"{int(iso.year)}-ISO{int(iso.week):02d}"
    return None


def _choose_latest_close(events: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    valid: list[tuple[pd.Timestamp, Mapping[str, Any]]] = []
    for event in events:
        ts = pd.to_datetime(event.get("captured_utc"), utc=True, errors="coerce")
        if pd.notna(ts):
            valid.append((ts, event))
    return max(valid, key=lambda pair: pair[0])[1] if valid else None


def _choose_grade(events: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any] | None, str | None]:
    if not events:
        return None, None
    actuals = {_num(event.get("actual_result")) for event in events}
    actuals.discard(None)
    if len(actuals) > 1:
        return None, "conflicting_grade_actuals"
    valid: list[tuple[pd.Timestamp, Mapping[str, Any]]] = []
    for event in events:
        ts = pd.to_datetime(event.get("graded_utc"), utc=True, errors="coerce")
        if pd.notna(ts):
            valid.append((ts, event))
    if not valid:
        return None, "grade_timestamp_invalid"
    return max(valid, key=lambda pair: pair[0])[1], None


def join_history_events(
    forecast_receipts: Sequence[Mapping[str, Any]],
    closing_events: Sequence[Mapping[str, Any]] = (),
    grade_events: Sequence[Mapping[str, Any]] = (),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Join immutable originals to closes and grades without rewriting originals."""

    originals: dict[str, Mapping[str, Any]] = {}
    audit = {
        "forecast_receipts_received": len(forecast_receipts),
        "closing_events_received": len(closing_events),
        "grade_events_received": len(grade_events),
        "duplicate_identical_originals": 0,
        "invalid_original_hashes": 0,
        "conflicting_originals": 0,
        "grade_conflicts": 0,
        "excluded_reasons": {},
    }

    def exclude(reason: str) -> None:
        audit["excluded_reasons"][reason] = audit["excluded_reasons"].get(reason, 0) + 1

    for receipt in forecast_receipts:
        if receipt.get("event_type") != "FORECAST_ORIGINAL":
            exclude("not_forecast_original")
            continue
        fid = _text(receipt.get("forecast_id"))
        original = receipt.get("original_forecast")
        if not fid or not isinstance(original, Mapping):
            exclude("malformed_forecast_original")
            continue
        expected = _text(receipt.get("original_sha256"))
        actual_hash = original_sha256(original)
        if expected and expected != actual_hash:
            audit["invalid_original_hashes"] += 1
            exclude("original_sha256_mismatch")
            continue
        if fid in originals:
            if _canonical(originals[fid]) == _canonical(receipt):
                audit["duplicate_identical_originals"] += 1
                continue
            audit["conflicting_originals"] += 1
            raise PropsEvaluationError(f"conflicting immutable originals for forecast_id={fid}")
        originals[fid] = receipt

    closes_by: dict[str, list[Mapping[str, Any]]] = {}
    for event in closing_events:
        fid = _text(event.get("forecast_id"))
        if fid:
            closes_by.setdefault(fid, []).append(event)

    grades_by: dict[str, list[Mapping[str, Any]]] = {}
    for event in grade_events:
        fid = _text(event.get("forecast_id"))
        if fid:
            grades_by.setdefault(fid, []).append(event)

    rows: list[dict[str, Any]] = []
    for fid, receipt in originals.items():
        original = receipt["original_forecast"]
        model = original.get("model") if isinstance(original.get("model"), Mapping) else {}
        market = original.get("market") if isinstance(original.get("market"), Mapping) else {}
        quality = (
            original.get("data_quality")
            if isinstance(original.get("data_quality"), Mapping)
            else {}
        )
        close = _choose_latest_close(closes_by.get(fid, []))
        grade, grade_problem = _choose_grade(grades_by.get(fid, []))
        if grade_problem:
            audit["grade_conflicts"] += 1
            exclude(grade_problem)
        actual = _num(grade.get("actual_result")) if grade else None
        game_id = _text(original.get("game_id"))
        kickoff = original.get("kickoff_utc")
        forecast_ts = original.get("forecast_timestamp_utc")
        kickoff_dt = pd.to_datetime(kickoff, utc=True, errors="coerce")
        forecast_dt = pd.to_datetime(forecast_ts, utc=True, errors="coerce")
        horizon_hours = (
            float((kickoff_dt - forecast_dt).total_seconds() / 3600.0)
            if pd.notna(kickoff_dt) and pd.notna(forecast_dt)
            else np.nan
        )
        prop = _text(original.get("prop_type"))
        market_line = _num(market.get("line"))
        fair_line = _num(model.get("fair_line"))
        std = _num(model.get("standard_deviation"))
        model_over = _prob(model.get("over_probability"))
        model_under = _prob(model.get("under_probability"))
        model_push = _prob(model.get("push_probability"))
        model_td = _prob(model.get("td_probability"))
        market_over = _prob(market.get("no_vig_over_probability"))
        market_under = _prob(market.get("no_vig_under_probability"))
        market_td = _prob(market.get("no_vig_probability"))

        row = {
            "forecast_id": fid,
            "recorded_utc": receipt.get("recorded_utc"),
            "original_sha256": receipt.get("original_sha256"),
            "game_id": game_id,
            "player_id": _text(original.get("player_id")),
            "player": _text(original.get("player")),
            "position": _text(original.get("position")),
            "prop_type": prop,
            "signal_state": (_text(original.get("signal_state")) or "").upper() or None,
            "quality_state": (_text(quality.get("state")) or "").upper() or None,
            "model_version": _text(model.get("version") or original.get("model_version")),
            "forecast_timestamp_utc": forecast_ts,
            "kickoff_utc": kickoff,
            "week_key": _week_from_row(game_id, kickoff),
            "forecast_horizon_hours": horizon_hours,
            "actual_result": actual,
            "model_mean": _num(model.get("mean")),
            "model_median": _num(model.get("median")),
            "fair_line": fair_line,
            "model_sd": std,
            "pi_low": _num((model.get("prediction_interval") or {}).get("low"))
            if isinstance(model.get("prediction_interval"), Mapping)
            else None,
            "pi_high": _num((model.get("prediction_interval") or {}).get("high"))
            if isinstance(model.get("prediction_interval"), Mapping)
            else None,
            "pi_coverage": _prob((model.get("prediction_interval") or {}).get("coverage"))
            if isinstance(model.get("prediction_interval"), Mapping)
            else None,
            "model_p_over": model_over,
            "model_p_under": model_under,
            "model_p_push": model_push,
            "model_td_probability": model_td,
            "market_line": market_line,
            "market_p_over": market_over,
            "market_p_under": market_under,
            "market_td_probability": market_td,
            "market_over_price_american": _num(market.get("over_price_american")),
            "market_under_price_american": _num(market.get("under_price_american")),
            "market_td_price_american": _num(market.get("td_price_american")),
            "close_line": _num(close.get("line")) if close else None,
            "close_over_price_american": _num(close.get("over_price_american")) if close else None,
            "close_under_price_american": _num(close.get("under_price_american")) if close else None,
            "close_td_price_american": _num(close.get("td_price_american")) if close else None,
            "graded": grade is not None and actual is not None,
            "grade_result": _text(grade.get("grading_result")) if grade else None,
        }

        if fair_line is not None and market_line is not None and std and std > 0:
            row["standardized_line_edge_abs"] = abs(fair_line - market_line) / std
        else:
            row["standardized_line_edge_abs"] = np.nan

        if prop in LINE_MARKETS and model_over is not None and market_over is not None:
            row["probability_edge_abs"] = abs(model_over - market_over)
        elif prop in BINARY_TD_MARKETS and model_td is not None and market_td is not None:
            row["probability_edge_abs"] = abs(model_td - market_td)
        else:
            row["probability_edge_abs"] = np.nan

        rows.append(row)

    frame = pd.DataFrame(rows)
    audit["valid_originals"] = len(originals)
    audit["joined_rows"] = len(frame)
    return frame, audit


def _counts(frame: pd.DataFrame) -> SampleCounts:
    if frame.empty:
        return SampleCounts(0, 0, 0, 0)
    return SampleCounts(
        forecasts=int(len(frame)),
        unique_players=int(frame["player_id"].dropna().nunique()),
        unique_games=int(frame["game_id"].dropna().nunique()),
        unique_weeks=int(frame["week_key"].dropna().nunique()),
    )


def _cluster_bootstrap(
    frame: pd.DataFrame,
    statistic: Callable[[pd.DataFrame], float],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float | None, float | None]:
    games = [value for value in frame["game_id"].dropna().unique()]
    if len(games) < 2 or frame.empty:
        return None, None
    grouped = {game: frame[frame["game_id"].eq(game)] for game in games}
    rng = np.random.default_rng(seed)
    estimates: list[float] = []
    for _ in range(int(replicates)):
        sampled = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[game] for game in sampled], ignore_index=True)
        value = statistic(boot)
        if isfinite(value):
            estimates.append(float(value))
    if not estimates:
        return None, None
    return (
        float(np.quantile(estimates, 0.025)),
        float(np.quantile(estimates, 0.975)),
    )


def _wilson(successes: int, total: int, level: float = 0.95) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    z = NormalDist().inv_cdf(0.5 + level / 2.0)
    p = successes / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    half = z * sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total) / denom
    return max(0.0, center - half), min(1.0, center + half)


def continuous_metrics(frame: pd.DataFrame, *, bootstrap_replicates: int = BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    work = frame[
        frame["prop_type"].isin(CONTINUOUS_EVAL_MARKETS)
        & frame["actual_result"].notna()
        & frame["model_mean"].notna()
    ].copy()
    counts = _counts(work)
    if work.empty:
        return {"sample": counts.__dict__, "status": "NO_GRADED_CONTINUOUS_FORECASTS"}

    err = work["model_mean"].astype(float) - work["actual_result"].astype(float)
    out: dict[str, Any] = {
        "sample": counts.__dict__,
        "mae_model_mean": float(np.mean(np.abs(err))),
        "rmse_model_mean": float(np.sqrt(np.mean(np.square(err)))),
        "median_absolute_error_model_mean": float(np.median(np.abs(err))),
        "bias_model_mean": float(np.mean(err)),
        "mean_forecast": float(work["model_mean"].mean()),
        "mean_actual": float(work["actual_result"].mean()),
        "pearson_correlation_descriptive": (
            float(work[["model_mean", "actual_result"]].corr().iloc[0, 1])
            if len(work) >= 2
            else None
        ),
    }
    fair = work[work["fair_line"].notna()].copy()
    if not fair.empty:
        fair_err = fair["fair_line"].astype(float) - fair["actual_result"].astype(float)
        out["mae_fair_line"] = float(np.mean(np.abs(fair_err)))
        out["bias_fair_line"] = float(np.mean(fair_err))
    interval = work[
        work["pi_low"].notna() & work["pi_high"].notna() & work["pi_coverage"].notna()
    ].copy()
    if not interval.empty:
        covered = (
            (interval["actual_result"] >= interval["pi_low"])
            & (interval["actual_result"] <= interval["pi_high"])
        )
        out["prediction_interval_empirical_coverage"] = float(covered.mean())
        out["prediction_interval_nominal_coverage_mean"] = float(interval["pi_coverage"].mean())
        widths = interval["pi_high"].astype(float) - interval["pi_low"].astype(float)
        out["prediction_interval_mean_width"] = float(widths.mean())
        out["prediction_interval_median_width"] = float(widths.median())

    out["mae_model_mean_ci95_game_clustered"] = _cluster_bootstrap(
        work,
        lambda x: float(np.mean(np.abs(x["model_mean"].astype(float) - x["actual_result"].astype(float)))),
        replicates=bootstrap_replicates,
    )
    out["bias_model_mean_ci95_game_clustered"] = _cluster_bootstrap(
        work,
        lambda x: float(np.mean(x["model_mean"].astype(float) - x["actual_result"].astype(float))),
        replicates=bootstrap_replicates,
    )
    out["status"] = (
        "STABLE_SAMPLE"
        if counts.forecasts >= 50 and counts.unique_games >= 20 and counts.unique_weeks >= 3
        else "INSUFFICIENT_FOR_STABLE_SUBGROUP_CONCLUSION"
    )
    out["crps_status"] = "UNAVAILABLE_UNLESS_EXACT_FROZEN_DISTRIBUTION_IS_PRESERVED"
    out["pit_status"] = "UNAVAILABLE_UNLESS_EXACT_FROZEN_DISTRIBUTION_IS_PRESERVED"
    return out


def _probability_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        actual = _num(row.get("actual_result"))
        prop = _text(row.get("prop_type"))
        if actual is None or prop is None:
            continue
        if prop in LINE_MARKETS:
            line = _num(row.get("market_line"))
            over = _prob(row.get("model_p_over"))
            under = _prob(row.get("model_p_under"))
            if line is None or over is None or under is None or actual == line:
                continue
            denom = over + under
            if denom <= 0:
                continue
            model_p = over / denom
            market_p = _prob(row.get("market_p_over"))
            y = 1.0 if actual > line else 0.0
            kind = "OVER"
        elif prop in BINARY_TD_MARKETS:
            model_p = _prob(row.get("model_td_probability"))
            if model_p is None:
                continue
            market_p = _prob(row.get("market_td_probability"))
            y = 1.0 if actual >= 1.0 else 0.0
            kind = "TD"
        else:
            continue
        favored_p = model_p if model_p >= 0.5 else 1.0 - model_p
        favored_y = y if model_p >= 0.5 else 1.0 - y
        rows.append(
            {
                **row.to_dict(),
                "probability_event": kind,
                "model_probability": model_p,
                "market_probability": market_p,
                "event_observed": y,
                "favored_probability": favored_p,
                "favored_observed": favored_y,
            }
        )
    return pd.DataFrame(rows)


def _brier(work: pd.DataFrame, column: str) -> float:
    return float(np.mean(np.square(work[column].astype(float) - work["event_observed"].astype(float))))


def _log_loss(work: pd.DataFrame, column: str) -> float:
    p = np.clip(work[column].astype(float).to_numpy(), PROB_EPS, 1.0 - PROB_EPS)
    y = work["event_observed"].astype(float).to_numpy()
    return float(np.mean(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))))


def calibration_table(\n    prob_rows: pd.DataFrame,\n    *,\n    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,\n) -> list[dict[str, Any]]:
    if prob_rows.empty:
        return []
    out: list[dict[str, Any]] = []
    for low, high, label in FIXED_CALIBRATION_BINS:
        bucket = prob_rows[
            (prob_rows["favored_probability"] >= low)
            & (prob_rows["favored_probability"] < high)
        ].copy()
        counts = _counts(bucket)
        if bucket.empty:
            out.append(
                {
                    "bin": label,
                    "n": 0,
                    "unique_games": 0,
                    "mean_predicted_probability": None,
                    "observed_frequency": None,
                    "calibration_gap": None,
                    "observed_frequency_ci95_game_clustered": [None, None],
                    "status": "EMPTY",
                }
            )
            continue
        predicted = float(bucket["favored_probability"].mean())
        observed = float(bucket["favored_observed"].mean())
        ci = _cluster_bootstrap(
            bucket,
            lambda x: float(x["favored_observed"].mean()),
        )
        out.append(
            {
                "bin": label,
                "n": counts.forecasts,
                "unique_games": counts.unique_games,
                "mean_predicted_probability": predicted,
                "observed_frequency": observed,
                "calibration_gap": observed - predicted,
                "observed_frequency_ci95_game_clustered": list(ci),
                "status": (
                    "INFERENTIAL"
                    if counts.forecasts >= 25 and counts.unique_games >= 10
                    else "DESCRIPTIVE_SPARSE"
                ),
            }
        )
    return out


def probability_metrics(frame: pd.DataFrame, *, bootstrap_replicates: int = BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    work = _probability_rows(frame)
    counts = _counts(work)
    if work.empty:
        return {
            "sample": counts.__dict__,
            "status": "NO_GRADED_PROBABILITY_FORECASTS",
            "calibration": [],
        }
    out: dict[str, Any] = {
        "sample": counts.__dict__,
        "brier_model": _brier(work, "model_probability"),
        "log_loss_model": _log_loss(work, "model_probability"),
        "calibration_in_the_large": float(
            work["event_observed"].mean() - work["model_probability"].mean()
        ),
        "calibration": calibration_table(work, bootstrap_replicates=bootstrap_replicates),
    }
    nonempty_bins = [row for row in out["calibration"] if row["n"] > 0]
    if nonempty_bins:
        total = sum(row["n"] for row in nonempty_bins)
        out["expected_calibration_error"] = float(
            sum(row["n"] * abs(row["calibration_gap"]) for row in nonempty_bins) / total
        )

    matched = work[work["market_probability"].notna()].copy()
    matched_counts = _counts(matched)
    out["market_matched_sample"] = matched_counts.__dict__
    if not matched.empty:
        out["brier_market_no_vig"] = _brier(matched, "market_probability")
        out["log_loss_market_no_vig"] = _log_loss(matched, "market_probability")
        out["brier_difference_model_minus_market"] = (
            out["brier_model"]
            if len(matched) == len(work)
            else _brier(matched, "model_probability")
        ) - _brier(matched, "market_probability")
        out["log_loss_difference_model_minus_market"] = (
            _log_loss(matched, "model_probability") - _log_loss(matched, "market_probability")
        )
        out["brier_difference_ci95_game_clustered"] = list(
            _cluster_bootstrap(
                matched,
                lambda x: _brier(x, "model_probability") - _brier(x, "market_probability"),
                replicates=bootstrap_replicates,
            )
        )
        out["log_loss_difference_ci95_game_clustered"] = list(
            _cluster_bootstrap(
                matched,
                lambda x: _log_loss(x, "model_probability") - _log_loss(x, "market_probability"),
                replicates=bootstrap_replicates,
            )
        )
    out["status"] = (
        "STABLE_SAMPLE"
        if counts.forecasts >= 100 and counts.unique_games >= 30
        else "INSUFFICIENT_FOR_STABLE_CALIBRATION_CONCLUSION"
    )
    return out


def market_relative_metrics(
    frame: pd.DataFrame, *, bootstrap_replicates: int = BOOTSTRAP_REPLICATES
) -> dict[str, Any]:
    matched = frame[
        frame["prop_type"].isin(LINE_MARKETS)
        & frame["actual_result"].notna()
        & frame["fair_line"].notna()
        & frame["market_line"].notna()
    ].copy()
    counts = _counts(matched)
    out: dict[str, Any] = {"sample": counts.__dict__}
    if matched.empty:
        out["status"] = "NO_MATCHED_MARKET_OUTCOMES"
        return out

    fair_abs = np.abs(matched["fair_line"].astype(float) - matched["actual_result"].astype(float))
    market_abs = np.abs(matched["market_line"].astype(float) - matched["actual_result"].astype(float))
    out.update(
        {
            "mae_fair_line": float(fair_abs.mean()),
            "mae_original_market_line": float(market_abs.mean()),
            "paired_absolute_error_difference_fair_minus_market": float((fair_abs - market_abs).mean()),
            "paired_absolute_error_difference_ci95_game_clustered": list(
                _cluster_bootstrap(
                    matched,
                    lambda x: float(
                        (
                            np.abs(x["fair_line"].astype(float) - x["actual_result"].astype(float))
                            - np.abs(x["market_line"].astype(float) - x["actual_result"].astype(float))
                        ).mean()
                    ),
                    replicates=bootstrap_replicates,
                )
            ),
        }
    )

    close = matched[matched["close_line"].notna()].copy()
    close_counts = _counts(close)
    out["closing_matched_sample"] = close_counts.__dict__
    if not close.empty:
        close_abs = np.abs(close["close_line"].astype(float) - close["actual_result"].astype(float))
        fair_close_abs = np.abs(close["fair_line"].astype(float) - close["actual_result"].astype(float))
        out["mae_closing_market_line"] = float(close_abs.mean())
        out["paired_absolute_error_difference_fair_minus_close"] = float(
            (fair_close_abs - close_abs).mean()
        )
        out["fair_minus_close_ci95_game_clustered"] = list(
            _cluster_bootstrap(
                close,
                lambda x: float(
                    (
                        np.abs(x["fair_line"].astype(float) - x["actual_result"].astype(float))
                        - np.abs(x["close_line"].astype(float) - x["actual_result"].astype(float))
                    ).mean()
                ),
                replicates=bootstrap_replicates,
            )
        )

        clv_values: list[float] = []
        for _, row in close.iterrows():
            original_line = _num(row.get("market_line"))
            closing_line = _num(row.get("close_line"))
            model_over = _prob(row.get("model_p_over"))
            market_over = _prob(row.get("market_p_over"))
            if None in {original_line, closing_line, model_over, market_over}:
                continue
            side = "OVER" if model_over > market_over else "UNDER" if model_over < market_over else None
            if side == "OVER":
                clv_values.append(float(closing_line - original_line))
            elif side == "UNDER":
                clv_values.append(float(original_line - closing_line))
        if clv_values:
            out["threshold_clv_mean"] = float(np.mean(clv_values))
            out["positive_threshold_clv_rate"] = float(np.mean(np.asarray(clv_values) > 0.0))
            out["threshold_clv_n"] = len(clv_values)

    out["status"] = (
        "STABLE_MATCHED_SAMPLE"
        if counts.forecasts >= 50 and counts.unique_games >= 20
        else "INSUFFICIENT_FOR_STABLE_MARKET_COMPARISON"
    )
    return out


def betting_metrics(frame: pd.DataFrame, *, bootstrap_replicates: int = BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    edges = frame[frame["signal_state"].eq("MODEL EDGE") & frame["actual_result"].notna()].copy()
    counts = _counts(edges)
    if edges.empty:
        return {
            "sample": counts.__dict__,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "net_units": None,
            "roi": None,
            "status": "NOT_MEASURABLE_NO_ORIGINAL_MODEL_EDGE_OBSERVATIONS",
        }

    bets: list[dict[str, Any]] = []
    exclusions: dict[str, int] = {}
    for _, row in edges.iterrows():
        prop = _text(row.get("prop_type"))
        actual = _num(row.get("actual_result"))
        if prop in LINE_MARKETS:
            line = _num(row.get("market_line"))
            model_over = _prob(row.get("model_p_over"))
            model_under = _prob(row.get("model_p_under"))
            market_over = _prob(row.get("market_p_over"))
            market_under = _prob(row.get("market_p_under"))
            if None in {line, model_over, model_under, market_over, market_under, actual}:
                exclusions["missing_line_probability"] = exclusions.get("missing_line_probability", 0) + 1
                continue
            over_edge = model_over - market_over
            under_edge = model_under - market_under
            side = "OVER" if over_edge > under_edge else "UNDER" if under_edge > over_edge else None
            if side is None or max(over_edge, under_edge) <= 0:
                exclusions["no_positive_edge_or_tie"] = exclusions.get("no_positive_edge_or_tie", 0) + 1
                continue
            price = (
                _num(row.get("market_over_price_american"))
                if side == "OVER"
                else _num(row.get("market_under_price_american"))
            )
            outcome = "PUSH" if actual == line else "OVER" if actual > line else "UNDER"
            result = "PUSH" if outcome == "PUSH" else "WIN" if outcome == side else "LOSS"
        elif prop in BINARY_TD_MARKETS:
            model_p = _prob(row.get("model_td_probability"))
            market_p = _prob(row.get("market_td_probability"))
            if None in {model_p, market_p, actual}:
                exclusions["missing_td_probability"] = exclusions.get("missing_td_probability", 0) + 1
                continue
            side = "TD" if model_p > market_p else "NO_TD" if model_p < market_p else None
            if side != "TD":
                exclusions["no_td_price_not_preserved_or_tie"] = exclusions.get(
                    "no_td_price_not_preserved_or_tie", 0
                ) + 1
                continue
            price = _num(row.get("market_td_price_american"))
            event = "TD" if actual >= 1.0 else "NO_TD"
            result = "WIN" if event == side else "LOSS"
        else:
            exclusions["unsupported_prop"] = exclusions.get("unsupported_prop", 0) + 1
            continue

        decimal = american_to_decimal(price)
        if decimal is None:
            exclusions["selected_side_price_missing"] = exclusions.get("selected_side_price_missing", 0) + 1
            continue
        profit = decimal - 1.0 if result == "WIN" else -1.0 if result == "LOSS" else 0.0
        bets.append(
            {
                "game_id": row.get("game_id"),
                "forecast_id": row.get("forecast_id"),
                "result": result,
                "decimal_price": decimal,
                "profit": profit,
            }
        )

    if not bets:
        return {
            "sample": counts.__dict__,
            "eligible_bets": 0,
            "exclusions": exclusions,
            "status": "NOT_MEASURABLE_NO_PRICE_COMPLETE_MODEL_EDGE_BETS",
        }

    bet_frame = pd.DataFrame(bets)
    wins = int(bet_frame["result"].eq("WIN").sum())
    losses = int(bet_frame["result"].eq("LOSS").sum())
    pushes = int(bet_frame["result"].eq("PUSH").sum())
    n = len(bet_frame)
    net = float(bet_frame["profit"].sum())
    roi = net / n
    nonpush = wins + losses
    lo, hi = _wilson(wins, nonpush)
    roi_ci = _cluster_bootstrap(
        bet_frame,
        lambda x: float(x["profit"].sum() / len(x)) if len(x) else float("nan"),
        replicates=bootstrap_replicates,
    )
    avg_decimal = float(bet_frame["decimal_price"].mean())
    return {
        "sample": counts.__dict__,
        "eligible_bets": n,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate_nonpush": wins / nonpush if nonpush else None,
        "win_rate_ci95_wilson": [lo, hi],
        "average_decimal_price": avg_decimal,
        "average_break_even_probability": float(np.mean(1.0 / bet_frame["decimal_price"])),
        "net_units": net,
        "roi": roi,
        "roi_ci95_game_clustered": list(roi_ci),
        "exclusions": exclusions,
        "status": (
            "STABLE_BETTING_SAMPLE"
            if n >= 100 and bet_frame["game_id"].nunique() >= 30
            else "INSUFFICIENT_FOR_STABLE_ROI_CONCLUSION"
        ),
    }


def _group_summary(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    if frame.empty or column not in frame.columns:
        return {}
    out: dict[str, Any] = {}
    for value, group in frame.groupby(column, dropna=False):
        key = "<MISSING>" if pd.isna(value) else str(value)
        counts = _counts(group)
        cont = continuous_metrics(group, bootstrap_replicates=1000)
        prob = probability_metrics(group, bootstrap_replicates=1000)
        out[key] = {
            "sample": counts.__dict__,
            "continuous": {
                k: cont.get(k)
                for k in ("mae_model_mean", "mae_fair_line", "bias_model_mean", "status")
            },
            "probability": {
                k: prob.get(k)
                for k in ("brier_model", "log_loss_model", "expected_calibration_error", "status")
            },
        }
    return out


def add_preregistered_bins(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if out.empty:
        for name in ("probability_edge_bin", "standardized_line_edge_bin", "forecast_horizon_bin"):
            out[name] = pd.Series(dtype="object")
        return out
    out["probability_edge_bin"] = pd.cut(
        pd.to_numeric(out["probability_edge_abs"], errors="coerce"),
        bins=[0.0, 0.025, 0.05, 0.075, 0.10, np.inf],
        right=False,
        labels=["0-2.5%", "2.5-5%", "5-7.5%", "7.5-10%", "10%+"],
    )
    out["standardized_line_edge_bin"] = pd.cut(
        pd.to_numeric(out["standardized_line_edge_abs"], errors="coerce"),
        bins=[0.0, 0.25, 0.50, 1.00, np.inf],
        right=False,
        labels=["0-0.25 SD", "0.25-0.50 SD", "0.50-1.00 SD", "1.00+ SD"],
    )
    out["forecast_horizon_bin"] = pd.cut(
        pd.to_numeric(out["forecast_horizon_hours"], errors="coerce"),
        bins=[0.0, 6.0, 24.0, 48.0, np.inf],
        right=False,
        labels=["<6h", "6-<24h", "24-<48h", "48h+"],
    )
    return out


def evaluate_history(
    forecast_receipts: Sequence[Mapping[str, Any]],
    closing_events: Sequence[Mapping[str, Any]] = (),
    grade_events: Sequence[Mapping[str, Any]] = (),
    *,
    frozen_model_ref: str,
    source_provenance: Mapping[str, Any] | None = None,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
) -> tuple[dict[str, Any], pd.DataFrame]:
    frame, audit = join_history_events(forecast_receipts, closing_events, grade_events)
    frame = add_preregistered_bins(frame)
    graded = frame[frame["actual_result"].notna()].copy() if not frame.empty else frame
    counts = _counts(frame)
    graded_counts = _counts(graded)

    summary = {
        "evaluation_contract_version": EVALUATION_CONTRACT_VERSION,
        "frozen_model_ref": frozen_model_ref,
        "source_provenance": dict(source_provenance or {}),
        "audit": audit,
        "sample": counts.__dict__,
        "graded_sample": graded_counts.__dict__,
        "continuous": continuous_metrics(frame, bootstrap_replicates=bootstrap_replicates),
        "probability": probability_metrics(frame, bootstrap_replicates=bootstrap_replicates),
        "market_relative": market_relative_metrics(
            frame, bootstrap_replicates=bootstrap_replicates
        ),
        "betting": betting_metrics(frame, bootstrap_replicates=bootstrap_replicates),
        "subgroups": {
            "prop_type": _group_summary(frame, "prop_type"),
            "position": _group_summary(frame, "position"),
            "signal_state": _group_summary(frame, "signal_state"),
            "quality_state": _group_summary(frame, "quality_state"),
            "probability_edge_bin": _group_summary(frame, "probability_edge_bin"),
            "standardized_line_edge_bin": _group_summary(
                frame, "standardized_line_edge_bin"
            ),
            "forecast_horizon_bin": _group_summary(frame, "forecast_horizon_bin"),
        },
    }
    summary["claim_readiness"] = {
        "projection_accuracy": graded_counts.forecasts >= 50
        and graded_counts.unique_games >= 20
        and graded_counts.unique_weeks >= 3,
        "calibration": summary["probability"]["sample"]["forecasts"] >= 100
        and summary["probability"]["sample"]["unique_games"] >= 30,
        "market_superiority": summary["market_relative"]["sample"]["forecasts"] >= 50
        and summary["market_relative"]["sample"]["unique_games"] >= 20,
        "roi": summary["betting"].get("eligible_bets", 0) >= 100,
    }
    return summary, frame
