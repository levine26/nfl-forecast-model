from __future__ import annotations

"""Generate the prospective LevLine 4 accuracy-first scoreboard.

This is research-only. It consumes immutable shadow forecasts plus official graded
history, enforces the strict T-minus contract, and reports winner-pick comparisons.
It never fits, retunes, selects, promotes, or changes a production forecast.
"""

import argparse
from datetime import timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.levline4_accuracy_primary_v1 import (
    PRIMARY_HORIZONS,
    horizon_pair_comparison,
    paired_accuracy_comparison,
)
from research.levline4_horizon_eligibility_v1 import (
    enforce_strict_cutoffs,
    horizon_completeness_audit,
)
from research.levline4_horizon_eval_v1 import score_rows
from research.levline4_horizon_shadow_v1 import (
    FST_HORIZON_CANDIDATE_ID,
    MARKET_CANDIDATE_ID,
)

PROSPECTIVE_START_UTC = pd.Timestamp("2026-09-12T16:33:37Z")
EPS = 1e-6


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _post_contract_games(shadows: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if shadows.empty or "kickoff_timestamp_utc" not in shadows.columns:
        return shadows.iloc[0:0].copy(), {
            "prospective_start_utc": PROSPECTIVE_START_UTC.isoformat(),
            "eligible_games": 0,
            "reason": "missing_kickoff_timestamp_utc_fail_closed",
        }
    kickoff = pd.to_datetime(shadows["kickoff_timestamp_utc"], utc=True, errors="coerce")
    # A game's accuracy-primary evidence is admissible only when its T-120 information
    # cutoff occurred after the objective was prospectively frozen.
    t120_cutoff = kickoff - pd.Timedelta(minutes=120)
    eligible = t120_cutoff.ge(PROSPECTIVE_START_UTC)
    filtered = shadows.loc[eligible].copy()
    return filtered, {
        "prospective_start_utc": PROSPECTIVE_START_UTC.isoformat(),
        "input_rows": int(len(shadows)),
        "eligible_rows": int(len(filtered)),
        "excluded_pre_contract_rows": int((~eligible).sum()),
        "eligible_games": int(filtered["game_id"].astype(str).nunique()) if "game_id" in filtered.columns else 0,
    }


def _incumbent_benchmark(candidate: pd.DataFrame) -> pd.DataFrame:
    if candidate.empty:
        return pd.DataFrame()
    work = candidate[candidate["incumbent_prob"].notna()].copy()
    if work.empty:
        return work
    p = pd.to_numeric(work["incumbent_prob"], errors="coerce")
    y = pd.to_numeric(work["home_win"], errors="coerce")
    valid = p.gt(0.0) & p.lt(1.0) & p.notna() & y.notna()
    work = work.loc[valid].copy()
    p = pd.to_numeric(work["incumbent_prob"], errors="raise").astype(float)
    y = pd.to_numeric(work["home_win"], errors="raise").astype(float)
    p_log = p.clip(EPS, 1.0 - EPS)
    work["winner_correct_eval"] = ((p >= 0.5).astype(float) == y).astype(float)
    work["brier_loss"] = (p - y) ** 2
    work["log_loss"] = -(y * np.log(p_log) + (1.0 - y) * np.log(1.0 - p_log))
    return work


def _candidate_vs_incumbent(candidate: pd.DataFrame, label: str) -> dict:
    benchmark = _incumbent_benchmark(candidate)
    if benchmark.empty:
        return {"benchmark": "official_T-120_F-ST", "candidate": label, "games": 0}
    result = paired_accuracy_comparison(
        candidate,
        benchmark,
        label="official_T-120_F-ST",
        join_on_horizon=True,
    )
    result["candidate"] = label
    return result


def _complete_case_games(frame: pd.DataFrame) -> set[str]:
    if frame.empty:
        return set()
    presence = (
        frame[["game_id", "horizon"]]
        .drop_duplicates()
        .groupby("game_id")["horizon"]
        .agg(lambda values: set(str(v) for v in values))
    )
    required = set(PRIMARY_HORIZONS)
    return {str(game_id) for game_id, horizons in presence.items() if required.issubset(horizons)}


def build_report(shadows: pd.DataFrame, history: pd.DataFrame) -> dict:
    post_contract, sample_audit = _post_contract_games(shadows)
    strict = enforce_strict_cutoffs(post_contract)
    scored = score_rows(strict.frame, history)
    frame = scored.frame.copy()

    report: dict = {
        "contract_id": "LEVLINE4-ACCURACY-PRIMARY-V1",
        "status": "research_only",
        "production_authorized": False,
        "promotion_authorized": False,
        "prospective_sample": sample_audit,
        "strict_pit_audit": strict.audit,
        "capture_completeness": horizon_completeness_audit(strict.frame),
        "graded_rows": int(len(frame)),
        "excluded_ungraded_rows": int(scored.excluded_ungraded),
        "excluded_ties": int(scored.excluded_ties),
        "excluded_invalid_probability": int(scored.excluded_invalid_probability),
        "objective_primary": "straight_up_winner_accuracy",
        "probability_metrics_role": "secondary_diagnostics",
    }
    if frame.empty:
        report["gate_status"] = "awaiting_graded_post_contract_games"
        return report

    market = frame[frame["candidate_id"].astype(str).eq(MARKET_CANDIDATE_ID)].copy()
    fst = frame[frame["candidate_id"].astype(str).eq(FST_HORIZON_CANDIDATE_ID)].copy()

    common_market_games = _complete_case_games(market)
    common_market = market[market["game_id"].astype(str).isin(common_market_games)].copy()
    report["raw_market_all_four_complete_case_games"] = int(len(common_market_games))
    report["raw_market_horizon_accuracy"] = {
        horizon: {
            "games": int(len(part)),
            "correct": int(part["winner_correct_eval"].sum()),
            "accuracy": float(part["winner_correct_eval"].mean()) if len(part) else None,
            "brier": float(part["brier_loss"].mean()) if len(part) else None,
        }
        for horizon in PRIMARY_HORIZONS
        for part in [common_market[common_market["horizon"].astype(str).eq(horizon)]]
    }
    report["raw_market_horizon_pairwise_accuracy"] = {
        f"{candidate}_vs_{benchmark}": horizon_pair_comparison(common_market, candidate, benchmark)
        for candidate in PRIMARY_HORIZONS
        for benchmark in PRIMARY_HORIZONS
        if candidate != benchmark
    }

    comparisons: dict[str, dict] = {}
    for family_name, family in (("raw_market", market), ("same_horizon_fst", fst)):
        comparisons[family_name] = {}
        for horizon in PRIMARY_HORIZONS:
            part = family[family["horizon"].astype(str).eq(horizon)].copy()
            comparisons[family_name][horizon] = _candidate_vs_incumbent(
                part,
                f"{family_name}:{horizon}",
            )
    report["candidate_vs_incumbent_accuracy"] = comparisons

    # The formal 200-game/14-week checkpoint is an earliest review gate only. It is
    # intentionally not a promotion switch.
    post_games = int(frame["game_id"].astype(str).nunique())
    if "week_official" in frame.columns:
        weeks = frame[["season_official", "week_official"]].dropna().drop_duplicates()
    elif {"season", "week"}.issubset(frame.columns):
        weeks = frame[["season", "week"]].dropna().drop_duplicates()
    else:
        weeks = pd.DataFrame()
    report["eligible_graded_games"] = post_games
    report["distinct_graded_weeks"] = int(len(weeks))
    report["earliest_formal_checkpoint_reached"] = bool(post_games >= 200 and len(weeks) >= 14)
    report["gate_status"] = (
        "formal_accuracy_review_eligible_not_auto_promotion"
        if report["earliest_formal_checkpoint_reached"]
        else "accumulating_prospective_accuracy_evidence"
    )
    return report


def run(
    *,
    shadow_path: str = "research_outputs/market_capture_v2/levline4_horizon_shadow.csv",
    prediction_history_path: str = "outputs/prediction_history.csv",
    report_path: str = "research_outputs/market_capture_v2/levline4_accuracy_primary_v1.json",
) -> dict:
    shadows = _read_csv(Path(shadow_path))
    history = _read_csv(Path(prediction_history_path))
    report = build_report(shadows, history)
    report["generated_at_utc"] = pd.Timestamp.now(tz=timezone.utc).isoformat()
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow", default="research_outputs/market_capture_v2/levline4_horizon_shadow.csv")
    parser.add_argument("--prediction-history", default="outputs/prediction_history.csv")
    parser.add_argument("--report", default="research_outputs/market_capture_v2/levline4_accuracy_primary_v1.json")
    args = parser.parse_args()
    result = run(
        shadow_path=args.shadow,
        prediction_history_path=args.prediction_history,
        report_path=args.report,
    )
    print(json.dumps({
        "gate_status": result.get("gate_status"),
        "eligible_graded_games": result.get("eligible_graded_games", 0),
        "production_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
