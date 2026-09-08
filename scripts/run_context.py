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
from nfl_forecast.injuries import fetch_nfl_injuries, practice_status_evidence
from nfl_forecast.narrative import build_game_previews


def _pandas(frame):
    if frame is None:
        return None
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _load_best_effort(season: int, cache_dir: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None, dict]:
    configure_cache(cache_dir)
    status = {}

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


def _fetch_injuries(season: int, week: int):
    """Prefer the official NFL injury report; retain ESPN as a fail-safe only."""
    nfl_rows, nfl_status = fetch_nfl_injuries(season, week)
    if nfl_status.get("status") == "healthy":
        return nfl_rows, nfl_status, True

    espn_rows, espn_status = fetch_espn_injuries()
    combined = {
        "status": "degraded",
        "provider": "NFL.com primary / ESPN fallback",
        "primary": nfl_status,
        "fallback": espn_status,
        "source": nfl_status.get("source"),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
    return espn_rows, combined, False


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

    week_values = pd.to_numeric(predictions.get("week"), errors="coerce").dropna()
    if week_values.empty:
        raise SystemExit("Prediction feed does not contain a valid week number")
    week = int(week_values.iloc[0])

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

    injuries, injury_status, official_injuries = _fetch_injuries(args.season, week)
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

    if official_injuries:
        for items in evidence.values():
            for item in items:
                if item.get("category") in {"personnel", "scenario"} and "ESPN" in str(item.get("source_name", "")):
                    item["source_name"] = "NFL.com official injury report"
                    item["summary"] = str(item.get("summary", "")).replace("ESPN currently lists", "The official NFL injury report lists")
        practice = practice_status_evidence(predictions, injuries)
        for gid, items in practice.items():
            evidence.setdefault(gid, []).extend(items)

    for items in evidence.values():
        for item in items:
            if item.get("category") == "structural_change":
                item["category"] = "coaching"
        rank = {"Strong": 3, "Moderate": 2, "Weak": 1}
        items.sort(key=lambda x: (rank.get(x.get("strength"), 0), x.get("category", "")), reverse=True)
        del items[12:]

    previews = build_game_previews(predictions, evidence)

    source_status.update(context_status)
    source_status["evidence"] = {
        "status":"healthy",
        "games":len(evidence),
        "signals":sum(len(v) for v in evidence.values()),
        "generated_utc":generated,
        "guardrail":"Context is explanatory only unless a feature is separately validated and promoted into the numerical model.",
    }
    source_status["previews"] = {
        "status": "healthy",
        "games": len(previews),
        "generator": "deterministic evidence composer",
        "guardrail": "Written previews may synthesize verified context but do not alter numerical probabilities.",
    }

    (out / "contextual_evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    (out / "game_previews.json").write_text(json.dumps(previews, indent=2, sort_keys=True), encoding="utf-8")
    (out / "context_source_status.json").write_text(json.dumps(source_status, indent=2, sort_keys=True), encoding="utf-8")

    counts = {gid: len(items) for gid, items in evidence.items()}
    print(f"Context refresh complete: {sum(counts.values())} evidence signals across {len(counts)} games")
    print(f"Written previews generated: {len(previews)}")
    print(json.dumps(source_status, indent=2))


if __name__ == "__main__":
    main()
