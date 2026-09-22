from __future__ import annotations

"""Live research-only runner for Adaptive Candidate 4.

The runner may execute after the nominal T-60 cutoff to allow research-data branches to
settle, but every scientific input is independently constrained to its preregistered
no-later-than cutoff. It never loads game outcomes.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from research.adaptive_candidate4_qb_shock_v1 import build_qb_shock_rows
from research.adaptive_candidate4_shadow_v1 import append_immutable, build_candidate4_decisions

EASTERN = ZoneInfo("America/New_York")
MIN_MINUTES_TO_KICKOFF = 20.0
MAX_MINUTES_TO_KICKOFF = 55.0


def _kickoff_utc(gameday: object, gametime: object) -> datetime:
    local = datetime.strptime(
        f"{str(gameday)[:10]} {str(gametime)[:5]}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=EASTERN)
    return local.astimezone(timezone.utc)


def due_candidate4_cohorts(feed: pd.DataFrame, now_utc: datetime) -> list[list[dict]]:
    rows: list[dict] = []
    for row in feed.to_dict("records"):
        try:
            season = int(row.get("season"))
            week = int(row.get("week"))
            gameday = datetime.fromisoformat(str(row.get("gameday"))[:10])
            kickoff = _kickoff_utc(row.get("gameday"), row.get("gametime"))
        except (TypeError, ValueError):
            continue
        if season != 2026 or week < 3 or gameday.weekday() != 6:
            continue
        minutes = (kickoff - now_utc).total_seconds() / 60.0
        if not (MIN_MINUTES_TO_KICKOFF <= minutes <= MAX_MINUTES_TO_KICKOFF):
            continue
        rows.append(
            {
                "game_id": str(row.get("game_id")),
                "season": season,
                "week": week,
                "gameday": str(row.get("gameday")),
                "gametime": str(row.get("gametime")),
                "away_team": str(row.get("away_team")),
                "home_team": str(row.get("home_team")),
                "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
            }
        )

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["kickoff_utc"], []).append(row)
    return [
        sorted(group, key=lambda x: x["game_id"])
        for _, group in sorted(grouped.items())
    ]


def _read_csv(path: Path, *, usecols: list[str] | None = None) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, usecols=usecols)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _append_attempt(path: Path, payload: dict) -> None:
    existing = _read_jsonl(path)
    attempt_id = str(payload["attempt_id"])
    if any(str(row.get("attempt_id")) == attempt_id for row in existing):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def _load_depth_live() -> pd.DataFrame:
    import nflreadpy as nfl

    frame = nfl.load_depth_charts([2026])
    if hasattr(frame, "to_dicts"):
        return pd.DataFrame(frame.to_dicts())
    if hasattr(frame, "to_pandas"):
        return frame.to_pandas()
    return pd.DataFrame(frame)


def run(
    *,
    feed_path: Path,
    production_history_path: Path,
    market_ledger_path: Path,
    inactive_archive_dir: Path,
    output_dir: Path,
    now_utc: datetime | None = None,
    depth_frame: pd.DataFrame | None = None,
) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    feed = _read_csv(feed_path)
    cohorts = due_candidate4_cohorts(feed, now)
    if not cohorts:
        return {
            "status": "skipped",
            "reason": "no_candidate4_sunday_cohort_in_retry_window",
            "eligible_decisions_added": 0,
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    production_columns = [
        "game_id", "season", "week", "gameday", "home_team", "away_team",
        "final_home_prob", "lock_status", "lock_timestamp_utc", "kickoff_utc",
        "minutes_to_kickoff_at_lock", "fst_artifact_id", "final_probability_strategy",
    ]
    production = _read_csv(production_history_path, usecols=production_columns)
    market = _read_csv(market_ledger_path)
    depth = depth_frame if depth_frame is not None else _load_depth_live()

    ledger_path = output_dir / "candidate4_decisions.csv"
    existing = _read_csv(ledger_path)
    added = 0
    attempted = 0
    complete_qb_rows = 0

    for cohort in cohorts:
        game_ids = {str(game["game_id"]) for game in cohort}
        qb = build_qb_shock_rows(
            depth,
            archive_dir=inactive_archive_dir,
            games=cohort,
        )
        complete_qb_rows += int(qb.get("qb_state_complete", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())

        prod = production[production["game_id"].astype(str).isin(game_ids)].copy()
        decisions = build_candidate4_decisions(
            prod,
            market,
            qb,
            generated_at_utc=now,
        )
        for row in decisions.to_dict("records"):
            attempted += 1
            attempt_basis = "|".join(
                [
                    str(row.get("game_id")),
                    now.isoformat(),
                    str(row.get("decision_sha256")),
                    str(row.get("ineligibility_reasons") or ""),
                ]
            )
            _append_attempt(
                output_dir / "attempts.jsonl",
                {
                    "attempt_id": hashlib.sha256(attempt_basis.encode()).hexdigest(),
                    "attempted_at_utc": now.isoformat().replace("+00:00", "Z"),
                    "game_id": row.get("game_id"),
                    "eligible": bool(row.get("eligible")),
                    "ineligibility_reasons": row.get("ineligibility_reasons"),
                    "decision_sha256": row.get("decision_sha256"),
                    "qb_state_complete": row.get("qb_state_complete"),
                    "market_source_qualified": row.get("market_source_qualified"),
                    "research_only": True,
                    "production_authorized": False,
                    "completed_2026_outcomes_used": 0,
                },
            )

        eligible = decisions[decisions["eligible"].fillna(False).astype(bool)].copy() if not decisions.empty else decisions
        if not eligible.empty:
            before = len(existing)
            existing = append_immutable(existing, eligible)
            added += len(existing) - before

        qb_out = output_dir / "qb_state_attempts.csv"
        if qb_out.exists() and qb_out.stat().st_size:
            previous_qb = pd.read_csv(qb_out)
            qb_all = pd.concat([previous_qb, qb], ignore_index=True, sort=False)
        else:
            qb_all = qb.copy()
        if not qb_all.empty:
            qb_all = qb_all.drop_duplicates(["game_id", "qb_state_sha256"], keep="first")
            output_dir.mkdir(parents=True, exist_ok=True)
            qb_all.to_csv(qb_out, index=False)

    if not existing.empty:
        output_dir.mkdir(parents=True, exist_ok=True)
        existing.to_csv(ledger_path, index=False)

    status = {
        "status": "captured" if attempted else "skipped",
        "attempted_games": attempted,
        "complete_qb_rows": complete_qb_rows,
        "eligible_decisions_added": added,
        "total_immutable_decisions": len(existing),
        "run_timestamp_utc": now.isoformat().replace("+00:00", "Z"),
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "status.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--production-history", type=Path, default=Path("outputs/prediction_history.csv"))
    parser.add_argument(
        "--market-ledger",
        type=Path,
        default=Path("research_outputs/market_capture_v2/market_snapshots.csv"),
    )
    parser.add_argument(
        "--inactive-archive",
        type=Path,
        default=Path("research_outputs/inactive_article_source_archive_v1"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs/adaptive_candidate4_v1"),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                feed_path=args.feed,
                production_history_path=args.production_history,
                market_ledger_path=args.market_ledger,
                inactive_archive_dir=args.inactive_archive,
                output_dir=args.output_dir,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
