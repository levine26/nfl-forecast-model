from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import json

import nflreadpy as nfl
import pandas as pd

from nfl_forecast.context import (
    NFLVERSE_SCHEDULE_URL,
    build_contextual_evidence,
    fetch_espn_injuries,
    load_coaching_history,
)
from nfl_forecast.data import configure_cache


def _pandas(frame):
    if frame is None:
        return None
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _load_best_effort(season: int, cache_dir: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None, dict]:
    configure_cache(cache_dir)
    status = {}

    # Historical PBP deliberately stops before the forecast season. This avoids a package
    # current-season guard while still supporting QB/coordinator and scheme-history research.
    pbp_years = list(range(max(2020, season - 6), season))
    try:
        pbp = _pandas(nfl.load_pbp(pbp_years))
        status["pbp"] = {"status":"healthy", "seasons":pbp_years}
    except Exception as exc:
        pbp = None
        status["pbp"] = {"status":"degraded", "error":str(exc)[:240]}

    ftn_years = list(range(max(2022, season - 4), season + 1))
    try:
        ftn = _pandas(nfl.load_ftn_charting(ftn_years))
        status["ftn"] = {"status":"healthy", "requested_seasons":ftn_years}
    except Exception:
        try:
            fallback = [y for y in ftn_years if y < season]
            ftn = _pandas(nfl.load_ftn_charting(fallback))
            status["ftn"] = {"status":"healthy", "requested_seasons":fallback, "note":"current season charting not yet available"}
        except Exception as exc:
            ftn = None
            status["ftn"] = {"status":"degraded", "error":str(exc)[:240]}

    try:
        depth = _pandas(nfl.load_depth_charts(season))
        status["depth_charts"] = {"status":"healthy", "season":season}
    except Exception:
        try:
            depth = _pandas(nfl.load_depth_charts(season - 1))
            status["depth_charts"] = {"status":"degraded", "season":season-1, "note":"current season depth chart unavailable; QB-specific context may be stale"}
        except Exception as exc:
            depth = None
            status["depth_charts"] = {"status":"degraded", "error":str(exc)[:240]}

    return pbp, ftn, depth, status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--predictions", default="outputs/this_week.csv")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--cache-dir", default=".cache/nflreadpy")
    args = parser.parse_args()

    pred_path = Path(args.predictions)
    if not pred_path.exists():
        raise SystemExit(f"Missing predictions file: {pred_path}")
    predictions = pd.read_csv(pred_path)
    required = {"game_id","gameday","gametime","away_team","home_team"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise SystemExit(f"Prediction feed missing required fields: {missing}")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()

    source_status = {"generated_utc":generated}
    try:
        schedules = pd.read_csv(NFLVERSE_SCHEDULE_URL, low_memory=False)
        schedules = schedules[pd.to_numeric(schedules.get("season"), errors="coerce").eq(args.season)].copy()
        source_status["schedule"] = {"status":"healthy", "source":NFLVERSE_SCHEDULE_URL, "rows":int(len(schedules))}
    except Exception as exc:
        schedules = None
        source_status["schedule"] = {"status":"degraded", "source":NFLVERSE_SCHEDULE_URL, "error":str(exc)[:240]}

    injuries, injury_status = fetch_espn_injuries()
    source_status["injuries"] = injury_status

    teams = sorted(set(predictions["away_team"].astype(str)).union(predictions["home_team"].astype(str)))
    coaches, coach_status = load_coaching_history(
        teams=teams,
        season=args.season,
        cache_path=out / "coaching_cache.json",
        lookback=4,
    )
    source_status["coaching"] = coach_status

    pbp, ftn, depth, advanced_status = _load_best_effort(args.season, args.cache_dir)
    source_status.update(advanced_status)

    evidence, context_status = build_contextual_evidence(
        predictions=predictions,
        pbp=pbp,
        ftn=ftn,
        depth=depth,
        schedules=schedules,
        coaching_history=coaches,
        injuries=injuries,
        season=args.season,
    )
    # The current React app groups coaching/continuity evidence into the
    # "History vs. What's Different Now" section. Normalize the internal label at
    # publication time so the analytical engine can retain its more specific name.
    for items in evidence.values():
        for item in items:
            if item.get("category") == "structural_change":
                item["category"] = "coaching"

    source_status.update(context_status)
    source_status["evidence"] = {
        "status":"healthy",
        "games":len(evidence),
        "signals":sum(len(v) for v in evidence.values()),
        "generated_utc":generated,
        "guardrail":"Context is explanatory only unless a feature is separately validated and promoted into the numerical model.",
    }

    (out / "contextual_evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    (out / "context_source_status.json").write_text(json.dumps(source_status, indent=2, sort_keys=True), encoding="utf-8")

    counts = {gid: len(items) for gid, items in evidence.items()}
    print(f"Context refresh complete: {sum(counts.values())} evidence signals across {len(counts)} games")
    print(json.dumps(source_status, indent=2))


if __name__ == "__main__":
    main()
