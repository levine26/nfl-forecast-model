from __future__ import annotations

"""Postgame evaluation of the frozen Props 2.1 Week 2 prospective cohort.

This module is research-only. It never regenerates a pregame forecast, rewrites a
receipt, or mutates any production/forecast artifact. It adapts the exact frozen
Props 2.1 receipt blob into the metric contract that was preregistered on
2026-09-17, then joins finalized nflverse outcomes afterward.
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SHADOW_DIR = ROOT / "research" / "props" / "v2"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SHADOW_DIR))

import grade_prospective_football_shadow as shadow_grader  # noqa: E402
import props_accuracy_preregistered as prereg  # noqa: E402
from nfl_forecast.data import load_advanced_data, load_core_data  # noqa: E402
from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids  # noqa: E402
from nfl_forecast.props_upstream import normalize_nflverse_scramble_semantics  # noqa: E402


CONTRACT_VERSION = "levline-props-2.1-postgame-eval-v0.1.0"
P21_MODEL_VERSION = "levline-props-2.1-sunday-v0.1"
P21_RECEIPT_VERSION = "levline-props-2.1-prospective-receipt-v0.1"
V1_MODEL_VERSION = "levline-props-simulation-v0.1.0"
PUBLICATION_COMMIT = "ba723255982c79ffe6072c714dd0ee2c37e1fa34"
SOURCE_WORKFLOW_RUN = "35477049179"
EXPECTED_P21_BLOB = "e89cdce268fb10c5107ba6db4087107fb213555f"
EXPECTED_V1_BLOB = "ec61a5ae36f2e307b4bde1fc4c5a0fa6255923dc"
EXPECTED_RECEIPTS = 3439
EXPECTED_GAMES = (
    "2026_02_CAR_ATL",
    "2026_02_CIN_HOU",
    "2026_02_CLE_TB",
    "2026_02_GB_NYJ",
    "2026_02_IND_KC",
    "2026_02_JAX_DEN",
    "2026_02_LV_LAC",
    "2026_02_MIA_SF",
    "2026_02_MIN_CHI",
    "2026_02_NO_BAL",
    "2026_02_NYG_LA",
    "2026_02_PHI_TEN",
    "2026_02_PIT_NE",
    "2026_02_SEA_ARI",
    "2026_02_WAS_DAL",
)
SUPPORTED_PROPS = (
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "receptions",
    "passing_tds",
    "rushing_td",
    "receiving_td",
    "anytime_td",
)
LINE_PROPS = frozenset(
    {"passing_yards", "rushing_yards", "receiving_yards", "receptions", "passing_tds"}
)
TD_PROPS = frozenset({"rushing_td", "receiving_td", "anytime_td"})
EPS = 1e-12
BOOTSTRAP_SEED = 20260919


class Props21EvaluationError(RuntimeError):
    pass


def _aware(value: Any, *, label: str) -> pd.Timestamp:
    try:
        ts = pd.Timestamp(value)
    except Exception as exc:
        raise Props21EvaluationError(f"invalid timestamp: {label}") from exc
    if pd.isna(ts) or ts.tzinfo is None:
        raise Props21EvaluationError(f"timestamp must be timezone-aware: {label}")
    return ts.tz_convert("UTC")


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _prob(value: Any) -> float | None:
    out = _num(value)
    return out if out is not None and 0.0 <= out <= 1.0 else None


def _same_number(a: Any, b: Any, *, atol: float = 1e-12) -> bool:
    x = _num(a)
    y = _num(b)
    if x is None or y is None:
        return x is None and y is None
    return math.isclose(x, y, rel_tol=0.0, abs_tol=atol)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise Props21EvaluationError(f"missing receipt ledger: {path}")
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Props21EvaluationError(f"invalid JSONL at line {line_no}") from exc
        if not isinstance(row, dict):
            raise Props21EvaluationError(f"receipt line {line_no} is not an object")
        rows.append(row)
    return rows


def _read_v1(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise Props21EvaluationError(f"missing V1 forecast artifact: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("forecasts") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise Props21EvaluationError("V1 artifact must contain forecasts list")
    return [row for row in rows if isinstance(row, dict)]


def _require_sha256(value: Any, *, label: str) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise Props21EvaluationError(f"invalid SHA-256: {label}")
    return text


def verify_frozen_cohort(
    p21_receipts: Sequence[Mapping[str, Any]],
    v1_forecasts: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if len(p21_receipts) != EXPECTED_RECEIPTS:
        raise Props21EvaluationError(
            f"Props 2.1 receipt count drift: {len(p21_receipts)} != {EXPECTED_RECEIPTS}"
        )
    if len(v1_forecasts) != EXPECTED_RECEIPTS:
        raise Props21EvaluationError(
            f"V1 forecast count drift: {len(v1_forecasts)} != {EXPECTED_RECEIPTS}"
        )

    v1_index: dict[str, dict[str, Any]] = {}
    for row in v1_forecasts:
        fid = str(row.get("forecast_id") or "")
        if not fid or fid in v1_index:
            raise Props21EvaluationError(f"duplicate/invalid V1 forecast_id: {fid!r}")
        v1_index[fid] = dict(row)

    seen_receipts: set[str] = set()
    games: set[str] = set()
    market_hashes: set[str] = set()
    identity_mismatches: list[str] = []
    numeric_drift: list[str] = []

    for row in p21_receipts:
        if row.get("immutable") is not True:
            raise Props21EvaluationError("Props 2.1 receipt is not immutable")
        if row.get("production_authorized") is not False:
            raise Props21EvaluationError("Props 2.1 receipt is production-authorized")
        if row.get("outcome") is not None:
            raise Props21EvaluationError("pregame Props 2.1 receipt already contains outcome")
        if str(row.get("receipt_version") or "") != P21_RECEIPT_VERSION:
            raise Props21EvaluationError("unexpected Props 2.1 receipt version")
        if str(row.get("model_version") or "") != P21_MODEL_VERSION:
            raise Props21EvaluationError("unexpected Props 2.1 model version")

        f = row.get("forecast")
        if not isinstance(f, Mapping):
            raise Props21EvaluationError("Props 2.1 receipt missing forecast")
        rid = str(row.get("receipt_id") or "")
        fid = str(f.get("forecast_id") or "")
        if not rid or rid != fid or rid in seen_receipts:
            raise Props21EvaluationError(f"invalid/duplicate Props 2.1 receipt id: {rid!r}")
        seen_receipts.add(rid)

        source_id = str(f.get("source_v1_forecast_id") or "")
        v1 = v1_index.get(source_id)
        if v1 is None:
            raise Props21EvaluationError(f"missing exact V1 source forecast: {source_id!r}")

        for key in ("game_id", "player_id", "position", "prop_type", "team", "opponent"):
            p21_value = str(f.get(key) or "")
            v1_value = str(v1.get(key if key != "player_name" else "player") or "")
            if p21_value != v1_value:
                identity_mismatches.append(f"{fid}:{key}:{p21_value!r}!={v1_value!r}")

        prop = str(f.get("prop_type") or "")
        if prop not in SUPPORTED_PROPS:
            raise Props21EvaluationError(f"unsupported prop in cohort: {prop}")
        game_id = str(f.get("game_id") or "")
        games.add(game_id)

        provenance = f.get("provenance")
        if not isinstance(provenance, Mapping):
            raise Props21EvaluationError("Props 2.1 receipt missing provenance")
        if provenance.get("research_only") is not True:
            raise Props21EvaluationError("Props 2.1 receipt not marked research_only")
        if provenance.get("production_authorized") is not False:
            raise Props21EvaluationError("Props 2.1 provenance authorizes production")
        if str(provenance.get("challenger_model_version") or "") != P21_MODEL_VERSION:
            raise Props21EvaluationError("Props 2.1 challenger version drift")
        if str(provenance.get("source_v1_model_version") or "") != V1_MODEL_VERSION:
            raise Props21EvaluationError("Props 2.1 source V1 model version drift")

        horizon = _aware(provenance.get("source_data_horizon_utc"), label="source_data_horizon_utc")
        source_forecast = _aware(
            f.get("source_v1_forecast_timestamp_utc"),
            label="source_v1_forecast_timestamp_utc",
        )
        p21_forecast = _aware(f.get("forecast_timestamp_utc"), label="forecast_timestamp_utc")
        kickoff = _aware(f.get("kickoff_utc"), label="kickoff_utc")
        v1_forecast_ts = _aware(v1.get("forecast_timestamp_utc"), label="v1.forecast_timestamp_utc")
        v1_horizon = _aware(v1.get("data_horizon_utc"), label="v1.data_horizon_utc")
        if not (horizon <= source_forecast <= p21_forecast < kickoff):
            raise Props21EvaluationError(f"Props 2.1 chronology failure: {fid}")
        if source_forecast != v1_forecast_ts or horizon != v1_horizon:
            raise Props21EvaluationError(f"Props 2.1/V1 timestamp provenance mismatch: {fid}")

        market_sha = _require_sha256(
            provenance.get("source_market_sha256"),
            label=f"{fid}.source_market_sha256",
        )
        market_hashes.add(market_sha)

        market_state = f.get("market_state")
        if isinstance(market_state, Mapping) and market_state.get("latest_capture_utc"):
            market_at = _aware(
                market_state.get("latest_capture_utc"),
                label="market_state.latest_capture_utc",
            )
            if market_at > p21_forecast or market_at >= kickoff:
                raise Props21EvaluationError(f"future market evidence in receipt: {fid}")

        v1_model = v1.get("model") if isinstance(v1.get("model"), Mapping) else {}
        v1_market = v1.get("market") if isinstance(v1.get("market"), Mapping) else {}
        comparisons = (
            ("model_mean", f.get("model_mean"), v1_model.get("mean")),
            (
                "model_median",
                f.get("model_median"),
                v1_model.get("fair_line")
                if v1_model.get("fair_line") is not None
                else v1_model.get("median"),
            ),
            ("probability_over", f.get("probability_over"), v1_model.get("over_probability")),
            ("probability_td", f.get("probability_td"), v1_model.get("td_probability")),
            ("market_line", f.get("market_line"), v1_market.get("line")),
        )
        for label, p21_value, v1_value in comparisons:
            if not _same_number(p21_value, v1_value):
                numeric_drift.append(f"{fid}:{label}")

    if identity_mismatches:
        raise Props21EvaluationError(
            f"Props 2.1/V1 identity mismatch; first={identity_mismatches[0]}"
        )
    if numeric_drift:
        raise Props21EvaluationError(
            f"Props 2.1 numerical forecast drift vs frozen V1; first={numeric_drift[0]}"
        )

    expected_games = set(EXPECTED_GAMES)
    if games != expected_games:
        raise Props21EvaluationError(
            f"cohort game drift: missing={sorted(expected_games-games)} extra={sorted(games-expected_games)}"
        )

    return v1_index, {
        "props21_receipts": len(p21_receipts),
        "v1_forecasts": len(v1_forecasts),
        "matched_v1_sources": len(p21_receipts),
        "game_count": len(games),
        "games": sorted(games),
        "unique_source_market_hashes": len(market_hashes),
        "numeric_identity_vs_v1": True,
        "numeric_fields_checked": [
            "model_mean",
            "model_median/fair_line",
            "probability_over",
            "probability_td",
            "market_line",
        ],
    }


def adapt_receipts(
    p21_receipts: Sequence[Mapping[str, Any]],
    v1_index: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, dict[str, Any]]]:
    """Adapt frozen Props 2.1 receipts to the pre-outcome evaluation schema.

    Missing under/push probabilities, SD and prediction intervals are restored only
    from the exact frozen V1 source forecast after verify_frozen_cohort() proves
    numerical identity on the quantities Props 2.1 preserved.
    """
    adapted: list[dict[str, Any]] = []
    p21_to_v1: dict[str, str] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for receipt in p21_receipts:
        f = receipt["forecast"]
        source_id = str(f["source_v1_forecast_id"])
        v1 = v1_index[source_id]
        v1_model = v1.get("model") if isinstance(v1.get("model"), Mapping) else {}
        v1_market = v1.get("market") if isinstance(v1.get("market"), Mapping) else {}
        qa = f.get("qa") if isinstance(f.get("qa"), Mapping) else {}
        role = f.get("role_state") if isinstance(f.get("role_state"), Mapping) else {}
        market_state = f.get("market_state") if isinstance(f.get("market_state"), Mapping) else {}
        provenance = f["provenance"]

        model = {
            "version": P21_MODEL_VERSION,
            "mean": f.get("model_mean"),
            "median": f.get("model_median"),
            "fair_line": f.get("model_median"),
            "standard_deviation": v1_model.get("standard_deviation"),
            "over_probability": f.get("probability_over"),
            "under_probability": v1_model.get("under_probability"),
            "push_probability": v1_model.get("push_probability"),
            "td_probability": f.get("probability_td"),
            "prediction_interval": v1_model.get("prediction_interval"),
            "simulation_accounting_ok": v1_model.get("simulation_accounting_ok"),
        }
        market = {
            "source": v1_market.get("source"),
            "captured_utc": v1_market.get("captured_utc"),
            "line": f.get("market_line"),
            "over_price_american": v1_market.get("over_price_american"),
            "under_price_american": v1_market.get("under_price_american"),
            "td_price_american": v1_market.get("td_price_american"),
            "no_vig_over_probability": f.get("market_probability_over"),
            "no_vig_under_probability": v1_market.get("no_vig_under_probability"),
            "no_vig_probability": f.get("market_probability_td"),
        }
        original = {
            "forecast_id": f["forecast_id"],
            "player_identity_resolved": True,
            "player_id": f["player_id"],
            "player": f["player_name"],
            "position": f["position"],
            "team": f["team"],
            "opponent": f["opponent"],
            "game_id": f["game_id"],
            "prop_type": f["prop_type"],
            "forecast_timestamp_utc": f["forecast_timestamp_utc"],
            "data_horizon_utc": provenance["source_data_horizon_utc"],
            "kickoff_utc": f["kickoff_utc"],
            "signal_state": qa.get("signal_state"),
            "market": market,
            "model": model,
            "data_quality": v1.get("data_quality") if isinstance(v1.get("data_quality"), Mapping) else {},
            "evaluation_provenance": {
                "source_v1_forecast_id": source_id,
                "source_publication_commit": PUBLICATION_COMMIT,
                "source_props21_blob_sha": EXPECTED_P21_BLOB,
                "source_v1_blob_sha": EXPECTED_V1_BLOB,
                "adapter_postgame": True,
            },
        }
        adapted_hash = prereg.original_sha256(original)
        adapted.append(
            {
                "history_contract_version": "levline-props-2.1-evaluation-adapter-v0.1",
                "event_type": "FORECAST_ORIGINAL",
                "forecast_id": f["forecast_id"],
                "recorded_utc": receipt["captured_utc"],
                "original_sha256": adapted_hash,
                "original_forecast": original,
                "source_receipt_id": receipt["receipt_id"],
                "source_v1_forecast_id": source_id,
                "source_props21_blob_sha": EXPECTED_P21_BLOB,
            }
        )
        p21_to_v1[str(f["forecast_id"])] = source_id
        metadata[str(f["forecast_id"])] = {
            "source_v1_forecast_id": source_id,
            "qa_classification": qa.get("classification"),
            "qa_signal_state": qa.get("signal_state"),
            "qa_flag_codes": list(qa.get("flag_codes") or []),
            "qa_reason_tag_codes": list(qa.get("reason_tag_codes") or []),
            "market_distribution_status": market_state.get("status"),
            "market_distribution_reasons": list(market_state.get("reasons") or []),
            "book_count": _num(market_state.get("book_count")),
            "line_dispersion": _num(market_state.get("line_dispersion")),
            "availability": role.get("availability"),
            "role_state": role.get("state"),
            "workload_state": role.get("workload"),
            "role_uncertainty": role.get("uncertainty"),
            "qualified_evidence_count": len(role.get("evidence_ids") or []),
            "xtd_mode": (
                (f.get("xtd") or {}).get("mode")
                if isinstance(f.get("xtd"), Mapping)
                else None
            ),
            "source_v1_signal_state": v1.get("signal_state"),
        }
    return adapted, p21_to_v1, metadata


def _id_col(frame: pd.DataFrame, candidates: Sequence[str], *, label: str) -> str:
    for col in candidates:
        if col in frame.columns:
            return col
    raise Props21EvaluationError(f"PBP missing {label} player identity")


def _value_col(frame: pd.DataFrame, candidates: Sequence[str], *, label: str) -> str:
    for col in candidates:
        if col in frame.columns:
            return col
    raise Props21EvaluationError(f"PBP missing {label} value")


def _flag(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    return pd.to_numeric(frame[column], errors="coerce").fillna(0).eq(1)


def _aggregate_sum(
    pbp: pd.DataFrame,
    *,
    prop: str,
    id_col: str,
    value_col: str,
    mask: pd.Series,
) -> dict[tuple[str, str, str], float]:
    ids = pbp[id_col].astype("string").fillna("").str.strip()
    vals = pd.to_numeric(pbp[value_col], errors="coerce")
    work = pd.DataFrame(
        {
            "game_id": pbp["game_id"].astype(str),
            "player_id": ids,
            "value": vals,
        }
    )
    work = work[mask & ids.ne("") & vals.notna()].copy()
    grouped = work.groupby(["game_id", "player_id"], sort=False)["value"].sum()
    return {
        (str(game_id), str(player_id), prop): float(value)
        for (game_id, player_id), value in grouped.items()
    }


def _aggregate_count(
    pbp: pd.DataFrame,
    *,
    prop: str,
    id_col: str,
    mask: pd.Series,
) -> dict[tuple[str, str, str], float]:
    ids = pbp[id_col].astype("string").fillna("").str.strip()
    work = pd.DataFrame({"game_id": pbp["game_id"].astype(str), "player_id": ids})
    work = work[mask & ids.ne("")].copy()
    grouped = work.groupby(["game_id", "player_id"], sort=False).size()
    return {
        (str(game_id), str(player_id), prop): float(value)
        for (game_id, player_id), value in grouped.items()
    }


def actual_player_stats(pbp: pd.DataFrame) -> dict[tuple[str, str, str], float]:
    if "game_id" not in pbp.columns:
        raise Props21EvaluationError("PBP missing game_id")

    passer = _id_col(pbp, ("passer_player_id", "passer_id"), label="passer")
    rusher = _id_col(pbp, ("rusher_player_id", "rusher_id"), label="rusher")
    receiver = _id_col(pbp, ("receiver_player_id", "receiver_id"), label="receiver")
    passing_yards = _value_col(pbp, ("passing_yards", "yards_gained"), label="passing yards")
    rushing_yards = _value_col(pbp, ("rushing_yards", "yards_gained"), label="rushing yards")
    receiving_yards = _value_col(pbp, ("receiving_yards", "yards_gained"), label="receiving yards")

    complete = _flag(pbp, "complete_pass")
    rush_attempt = _flag(pbp, "rush_attempt")
    pass_td = _flag(pbp, "pass_touchdown")
    rush_td = _flag(pbp, "rush_touchdown")

    out: dict[tuple[str, str, str], float] = {}
    # If passing_yards falls back to yards_gained, count only completed passes so
    # sacks/interception returns cannot leak into passing production.
    pass_mask = pd.Series(True, index=pbp.index)
    if passing_yards == "yards_gained":
        pass_mask = complete

    for part in (
        _aggregate_sum(
            pbp,
            prop="passing_yards",
            id_col=passer,
            value_col=passing_yards,
            mask=pass_mask,
        ),
        _aggregate_sum(
            pbp,
            prop="rushing_yards",
            id_col=rusher,
            value_col=rushing_yards,
            mask=rush_attempt,
        ),
        _aggregate_sum(
            pbp,
            prop="receiving_yards",
            id_col=receiver,
            value_col=receiving_yards,
            mask=complete,
        ),
        _aggregate_count(pbp, prop="receptions", id_col=receiver, mask=complete),
        _aggregate_count(pbp, prop="passing_tds", id_col=passer, mask=pass_td),
        _aggregate_count(pbp, prop="rushing_td", id_col=rusher, mask=rush_td),
        _aggregate_count(pbp, prop="receiving_td", id_col=receiver, mask=pass_td),
    ):
        out.update(part)

    keys = {
        (game_id, player_id)
        for game_id, player_id, prop in out
        if prop in {"rushing_td", "receiving_td"}
    }
    for game_id, player_id in keys:
        rush = out.get((game_id, player_id, "rushing_td"), 0.0)
        rec = out.get((game_id, player_id, "receiving_td"), 0.0)
        out[(game_id, player_id, "anytime_td")] = float(rush + rec)
    return out


def build_grade_events(
    adapted_receipts: Sequence[Mapping[str, Any]],
    *,
    completed_games: set[str],
    outcome_pbp_games: set[str],
    actuals: Mapping[tuple[str, str, str], float],
    participation: Mapping[tuple[str, str], int],
    graded_utc: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    events: list[dict[str, Any]] = []
    audit = {
        "not_final": 0,
        "missing_final_pbp": 0,
        "missing_participation": 0,
        "zero_offense_snaps_void": 0,
        "graded": 0,
    }
    for receipt in adapted_receipts:
        original = receipt["original_forecast"]
        game_id = str(original["game_id"])
        if game_id not in completed_games:
            audit["not_final"] += 1
            continue
        if game_id not in outcome_pbp_games:
            audit["missing_final_pbp"] += 1
            continue
        player_id = str(original["player_id"])
        snaps = participation.get((game_id, player_id))
        if snaps is None:
            audit["missing_participation"] += 1
            continue
        if int(snaps) <= 0:
            audit["zero_offense_snaps_void"] += 1
            continue
        prop = str(original["prop_type"])
        actual = float(actuals.get((game_id, player_id, prop), 0.0))
        events.append(
            {
                "history_contract_version": "levline-props-2.1-postgame-grade-v0.1",
                "event_type": "GRADE",
                "forecast_id": receipt["forecast_id"],
                "graded_utc": graded_utc,
                "actual_result": actual,
                "original_sha256": receipt["original_sha256"],
                "grading_result": "FINAL_OFFICIAL_STAT",
                "result_source": "nflverse_finalized_pbp",
            }
        )
    audit["graded"] = len(events)
    return events, audit


def _cluster_ci(
    frame: pd.DataFrame,
    value_col: str,
    *,
    seed: int,
    replicates: int,
) -> list[float | None]:
    work = frame[["game_id", value_col]].copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work[work[value_col].notna()]
    if work.empty:
        return [None, None]
    grouped = work.groupby("game_id", sort=True)[value_col].agg(["sum", "count"])
    if len(grouped) < 2:
        return [None, None]
    sums = grouped["sum"].to_numpy(dtype=float)
    counts = grouped["count"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    values = np.empty(int(replicates), dtype=float)
    n_games = len(grouped)
    for i in range(int(replicates)):
        sampled = rng.integers(0, n_games, size=n_games)
        values[i] = float(sums[sampled].sum() / counts[sampled].sum())
    return [
        float(np.quantile(values, 0.025)),
        float(np.quantile(values, 0.975)),
    ]


def by_prop_primary_metrics(
    detail: pd.DataFrame,
    *,
    bootstrap_replicates: int,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for idx, prop in enumerate(SUPPORTED_PROPS):
        part = detail[detail["prop_type"].eq(prop) & detail["actual_result"].notna()].copy()
        if part.empty:
            out[prop] = {"n": 0}
            continue
        result: dict[str, Any] = {
            "n": int(len(part)),
            "unique_games": int(part["game_id"].nunique()),
            "unique_players": int(part["player_id"].nunique()),
        }
        point = part[part["model_mean"].notna()].copy()
        if not point.empty:
            err = point["model_mean"].astype(float) - point["actual_result"].astype(float)
            result["point"] = {
                "n": int(len(point)),
                "mae_model_mean": float(np.abs(err).mean()),
                "rmse_model_mean": float(np.sqrt(np.square(err).mean())),
                "median_absolute_error_model_mean": float(np.median(np.abs(err))),
                "bias_model_mean": float(err.mean()),
            }
        fair = part[part["fair_line"].notna()].copy()
        if not fair.empty:
            fair_abs = np.abs(fair["fair_line"].astype(float) - fair["actual_result"].astype(float))
            fair_payload: dict[str, Any] = {
                "n": int(len(fair)),
                "mae_fair_line": float(fair_abs.mean()),
                "bias_fair_line": float(
                    (fair["fair_line"].astype(float) - fair["actual_result"].astype(float)).mean()
                ),
            }
            matched = fair[fair["market_line"].notna()].copy()
            if not matched.empty:
                matched["fair_abs"] = np.abs(
                    matched["fair_line"].astype(float) - matched["actual_result"].astype(float)
                )
                matched["market_abs"] = np.abs(
                    matched["market_line"].astype(float) - matched["actual_result"].astype(float)
                )
                matched["fair_minus_market_abs"] = matched["fair_abs"] - matched["market_abs"]
                fair_payload.update(
                    {
                        "market_matched_n": int(len(matched)),
                        "mae_market_line": float(matched["market_abs"].mean()),
                        "paired_mae_difference_fair_minus_market": float(
                            matched["fair_minus_market_abs"].mean()
                        ),
                        "paired_mae_difference_ci95_game_clustered": _cluster_ci(
                            matched,
                            "fair_minus_market_abs",
                            seed=BOOTSTRAP_SEED + idx * 100,
                            replicates=bootstrap_replicates,
                        ),
                    }
                )
            result["fair_line"] = fair_payload
        result["probability"] = prereg.probability_metrics(
            part,
            bootstrap_replicates=bootstrap_replicates,
        )
        out[prop] = result
    return out


def _liquidity_bucket(value: Any) -> str:
    n = _num(value)
    if n is None or n <= 0:
        return "0"
    if n <= 2:
        return "1-2"
    if n <= 4:
        return "3-4"
    return "5+"


def attach_frozen_metadata(
    detail: pd.DataFrame,
    metadata: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    if detail.empty:
        return detail
    out = detail.copy()
    metas = pd.DataFrame(
        [{"forecast_id": fid, **dict(values)} for fid, values in metadata.items()]
    )
    out = out.merge(metas, how="left", on="forecast_id", validate="one_to_one")
    out["market_liquidity_bucket"] = out["book_count"].map(_liquidity_bucket)
    return out


def _safe_corr(x: pd.Series, y: pd.Series) -> float | None:
    pair = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if len(pair) < 3 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
        return None
    value = pair["x"].corr(pair["y"])
    return float(value) if pd.notna(value) else None


def incremental_information_diagnostics(
    detail: pd.DataFrame,
    *,
    bootstrap_replicates: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "EXPLORATORY_SINGLE_WEEK_NO_FORMAL_ENCOMPASSING_CLAIM",
        "props21_vs_v1": {
            "numeric_identity": True,
            "interpretation": (
                "Props 2.1 and its exact frozen V1 source have identical point/probability forecasts "
                "for all 3,439 cohort rows; predictive score differences are therefore exactly zero."
            ),
        },
        "market_residual_tests": {},
    }
    for idx, prop in enumerate(LINE_PROPS):
        part = detail[
            detail["prop_type"].eq(prop)
            & detail["actual_result"].notna()
            & detail["fair_line"].notna()
            & detail["market_line"].notna()
        ].copy()
        if part.empty:
            result["market_residual_tests"][prop] = {"n": 0}
            continue
        part["model_market_delta"] = part["fair_line"].astype(float) - part["market_line"].astype(float)
        part["market_residual"] = part["actual_result"].astype(float) - part["market_line"].astype(float)
        part["fair_abs"] = np.abs(part["fair_line"].astype(float) - part["actual_result"].astype(float))
        part["market_abs"] = np.abs(part["market_line"].astype(float) - part["actual_result"].astype(float))
        part["fair_minus_market_abs"] = part["fair_abs"] - part["market_abs"]

        nonzero = part[
            ~np.isclose(part["model_market_delta"].astype(float), 0.0)
            & ~np.isclose(part["market_residual"].astype(float), 0.0)
        ].copy()
        direction = (
            float(
                (
                    np.sign(nonzero["model_market_delta"].astype(float))
                    == np.sign(nonzero["market_residual"].astype(float))
                ).mean()
            )
            if len(nonzero)
            else None
        )
        result["market_residual_tests"][prop] = {
            "n": int(len(part)),
            "unique_games": int(part["game_id"].nunique()),
            "corr_model_market_delta_vs_market_residual": _safe_corr(
                part["model_market_delta"], part["market_residual"]
            ),
            "disagreement_direction_accuracy_ex_pushes_and_ties": direction,
            "paired_mae_difference_fair_minus_market": float(part["fair_minus_market_abs"].mean()),
            "paired_mae_difference_ci95_game_clustered": _cluster_ci(
                part,
                "fair_minus_market_abs",
                seed=BOOTSTRAP_SEED + 7000 + idx * 100,
                replicates=bootstrap_replicates,
            ),
            "formal_incremental_signal_claim_authorized": False,
        }
    return result


def component_value_audit(
    p21_receipts: Sequence[Mapping[str, Any]],
    v1_index: Mapping[str, Mapping[str, Any]],
    detail: pd.DataFrame,
) -> dict[str, Any]:
    transitions: dict[str, int] = {}
    for row in p21_receipts:
        f = row["forecast"]
        v1 = v1_index[str(f["source_v1_forecast_id"])]
        p21_state = str((f.get("qa") or {}).get("signal_state") or "<MISSING>")
        v1_state = str(v1.get("signal_state") or "<MISSING>")
        key = f"{v1_state}->{p21_state}"
        transitions[key] = transitions.get(key, 0) + 1

    supported = sum(
        1
        for row in p21_receipts
        if isinstance(row["forecast"].get("market_state"), Mapping)
        and row["forecast"]["market_state"].get("status") == "MARKET_DISTRIBUTION_SUPPORTED"
    )
    fallback = len(p21_receipts) - supported
    qa_counts: dict[str, int] = {}
    for row in p21_receipts:
        state = str((row["forecast"].get("qa") or {}).get("signal_state") or "<MISSING>")
        qa_counts[state] = qa_counts.get(state, 0) + 1

    by_signal: dict[str, Any] = {}
    if not detail.empty and "qa_signal_state" in detail:
        for state, part in detail.groupby("qa_signal_state", dropna=False):
            key = "<MISSING>" if pd.isna(state) else str(state)
            by_signal[key] = {
                "n": int(len(part)),
                "graded_n": int(part["actual_result"].notna().sum()),
                "probability": prereg.probability_metrics(part, bootstrap_replicates=25),
            }

    return {
        "numerical_forecast_change_vs_v1": False,
        "predictive_score_delta_vs_v1": 0.0,
        "signal_state_transition_counts": dict(sorted(transitions.items())),
        "props21_signal_counts": dict(sorted(qa_counts.items())),
        "market_distribution_supported": supported,
        "market_distribution_fallback": fallback,
        "context_fitted_xtd_activated": False,
        "interpretation": (
            "For this cohort Props 2.1 functioned as an intelligence/QA/presentation layer. "
            "It did not change the underlying numerical V1 forecast, so personnel/news/market-distribution "
            "features cannot receive predictive-accuracy credit from this slate; their measurable effects "
            "are suppression, diagnostics and failure prevention."
        ),
        "graded_performance_by_props21_signal_state": by_signal,
    }


def failure_mode_diagnostics(detail: pd.DataFrame, *, limit: int = 30) -> dict[str, Any]:
    if detail.empty:
        return {"largest_misses": [], "taxonomy_counts": {}}
    work = detail[
        detail["actual_result"].notna()
        & detail["model_mean"].notna()
    ].copy()
    if work.empty:
        return {"largest_misses": [], "taxonomy_counts": {}}
    work["signed_error"] = work["model_mean"].astype(float) - work["actual_result"].astype(float)
    work["absolute_error"] = np.abs(work["signed_error"])
    sd = pd.to_numeric(work["model_sd"], errors="coerce")
    work["standardized_abs_error"] = np.where(
        sd.gt(0),
        work["absolute_error"] / sd,
        np.nan,
    )

    def classify(row: pd.Series) -> str:
        flags = set(row.get("qa_flag_codes") or [])
        availability = str(row.get("availability") or "")
        if "UNKNOWN_AVAILABILITY" in flags or availability == "UNKNOWN":
            return "pregame_availability_uncertainty"
        if {"ROLE_UNCERTAINTY", "OPPORTUNITY_UNVERIFIED"} & flags:
            return "pregame_role_workload_uncertainty"
        if (
            str(row.get("market_distribution_status") or "") != "MARKET_DISTRIBUTION_SUPPORTED"
            or (_num(row.get("book_count")) or 0) < 2
        ):
            return "thin_or_fallback_market_context"
        if str(row.get("prop_type") or "") in TD_PROPS | {"passing_tds"}:
            return "td_outcome_variance_candidate"
        return "unclassified_forecast_miss_needs_component_forensics"

    work["failure_taxonomy"] = work.apply(classify, axis=1)
    order = work.sort_values(
        ["standardized_abs_error", "absolute_error"],
        ascending=[False, False],
        na_position="last",
    ).head(limit)
    cols = [
        "forecast_id",
        "game_id",
        "player",
        "position",
        "prop_type",
        "actual_result",
        "model_mean",
        "fair_line",
        "market_line",
        "signed_error",
        "absolute_error",
        "standardized_abs_error",
        "qa_signal_state",
        "qa_classification",
        "qa_flag_codes",
        "availability",
        "role_state",
        "market_distribution_status",
        "book_count",
        "failure_taxonomy",
    ]
    rows = order[[c for c in cols if c in order.columns]].replace({np.nan: None}).to_dict("records")
    counts = work["failure_taxonomy"].value_counts().to_dict()
    return {
        "largest_misses": rows,
        "taxonomy_counts": {str(k): int(v) for k, v in counts.items()},
        "taxonomy_is_causal": False,
        "note": (
            "Taxonomy uses only frozen pregame QA evidence and market-state metadata. "
            "Unclassified rows require deeper component/game-film-data forensics before causal labeling."
        ),
    }


def descriptive_slices(detail: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for dimension in (
        "position",
        "market_liquidity_bucket",
        "availability",
        "role_state",
        "market_distribution_status",
        "qa_signal_state",
    ):
        groups: dict[str, Any] = {}
        if dimension not in detail.columns:
            out[dimension] = groups
            continue
        for value, part in detail.groupby(dimension, dropna=False):
            key = "<MISSING>" if pd.isna(value) else str(value)
            by_prop: dict[str, Any] = {}
            for prop, subset in part.groupby("prop_type", dropna=False):
                scored = subset[
                    subset["actual_result"].notna() & subset["model_mean"].notna()
                ].copy()
                if scored.empty:
                    continue
                err = scored["model_mean"].astype(float) - scored["actual_result"].astype(float)
                by_prop[str(prop)] = {
                    "n": int(len(scored)),
                    "unique_games": int(scored["game_id"].nunique()),
                    "mae_model_mean": float(np.abs(err).mean()),
                    "bias_model_mean": float(err.mean()),
                }
            groups[key] = by_prop
        out[dimension] = groups
    return out


def run(
    p21_path: Path,
    v1_path: Path,
    output_dir: Path,
    *,
    bootstrap_replicates: int = 5000,
) -> dict[str, Any]:
    p21_receipts = _read_jsonl(p21_path)
    v1_forecasts = _read_v1(v1_path)
    v1_index, cohort_audit = verify_frozen_cohort(p21_receipts, v1_forecasts)
    adapted, p21_to_v1, metadata = adapt_receipts(p21_receipts, v1_index)

    bundle = load_core_data([2026])
    bundle = load_advanced_data(bundle, [2026])
    schedule = bundle.schedules.to_pandas() if hasattr(bundle.schedules, "to_pandas") else bundle.schedules.copy()
    pbp = bundle.pbp.to_pandas() if hasattr(bundle.pbp, "to_pandas") else bundle.pbp.copy()
    pbp, scramble_audit = normalize_nflverse_scramble_semantics(pbp)

    players = nfl.load_players()
    players = players.to_pandas() if hasattr(players, "to_pandas") else players.copy()
    snaps, snap_identity_audit = normalize_snap_counts_player_ids(bundle.snap_counts, players)
    if snaps is None or snaps.empty:
        raise Props21EvaluationError(f"snap identity normalization failed: {snap_identity_audit}")
    participation, participation_audit = shadow_grader.offense_participation(snaps)
    completed_games = shadow_grader._completed_games(schedule)
    outcome_pbp_games, outcome_pbp_audit = shadow_grader.complete_outcome_pbp_games(pbp)
    actuals = actual_player_stats(pbp)

    graded_utc = datetime.now(timezone.utc).isoformat()
    grades, eligibility_audit = build_grade_events(
        adapted,
        completed_games=completed_games,
        outcome_pbp_games=outcome_pbp_games,
        actuals=actuals,
        participation=participation,
        graded_utc=graded_utc,
    )

    summary, detail = prereg.evaluate_history(
        adapted,
        (),
        grades,
        frozen_model_ref=f"{P21_MODEL_VERSION}@{PUBLICATION_COMMIT}",
        source_provenance={
            "source_workflow_run": SOURCE_WORKFLOW_RUN,
            "publication_commit": PUBLICATION_COMMIT,
            "props21_receipt_blob_sha": EXPECTED_P21_BLOB,
            "v1_forecast_blob_sha": EXPECTED_V1_BLOB,
            "postgame_adapter_contract": CONTRACT_VERSION,
            "preoutcome_metric_contract": prereg.EVALUATION_CONTRACT_VERSION,
        },
        bootstrap_replicates=bootstrap_replicates,
    )
    detail = attach_frozen_metadata(detail, metadata)
    if not detail.empty:
        detail["source_v1_forecast_id"] = detail["forecast_id"].map(p21_to_v1)

    summary["props21_postgame_contract_version"] = CONTRACT_VERSION
    summary["cohort_integrity"] = cohort_audit
    summary["eligibility_audit"] = eligibility_audit
    summary["outcome_source_audit"] = {
        "pbp_normalization": scramble_audit,
        "snap_identity": snap_identity_audit,
        "participation": participation_audit,
        "outcome_pbp": outcome_pbp_audit,
        "completed_cohort_games": sorted(set(EXPECTED_GAMES) & set(completed_games)),
        "unfinalized_cohort_games": sorted(set(EXPECTED_GAMES) - set(completed_games)),
    }
    summary["primary_by_prop"] = by_prop_primary_metrics(
        detail,
        bootstrap_replicates=bootstrap_replicates,
    )
    summary["incremental_information"] = incremental_information_diagnostics(
        detail,
        bootstrap_replicates=bootstrap_replicates,
    )
    summary["component_value"] = component_value_audit(
        p21_receipts,
        v1_index,
        detail,
    )
    summary["failure_modes"] = failure_mode_diagnostics(detail)
    summary["descriptive_slices"] = descriptive_slices(detail)
    summary["distribution_metrics"] = {
        "crps": "UNAVAILABLE_FROM_FROZEN_P21_AND_V1_SUMMARY_ARTIFACTS",
        "pit": "UNAVAILABLE_FROM_FROZEN_P21_AND_V1_SUMMARY_ARTIFACTS",
        "reason": (
            "Neither frozen artifact preserves a lossless empirical distribution for all Props 2.1 rows. "
            "No parametric distribution is assumed post hoc."
        ),
    }
    summary["governance"] = {
        "research_only": True,
        "production_authorized": False,
        "original_receipts_mutated": False,
        "model_tuned_from_outcomes": False,
        "automatic_promotion_authorized": False,
        "single_week_market_superiority_claim_authorized": False,
        "pooled_unit_mixed_point_metrics_are_primary": False,
        "primary_point_metrics_are_by_prop_family": True,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    detail.to_csv(output_dir / "forecast_level.csv", index=False)
    pd.DataFrame(summary["failure_modes"]["largest_misses"]).to_csv(
        output_dir / "largest_misses.csv",
        index=False,
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--props21-ledger", type=Path, required=True)
    parser.add_argument("--v1-forecasts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=5000)
    args = parser.parse_args()
    run(
        args.props21_ledger,
        args.v1_forecasts,
        args.output_dir,
        bootstrap_replicates=args.bootstrap_replicates,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
