from __future__ import annotations

"""Outcome-blind qualification audit for Candidate 3 historical market-path source.

This script deliberately does not load NFL results, F-ST predictions, or any 2026-season
outcomes. It validates the public v1.1.1 DuckDB market archive and quantifies whether
timestamped pre-kickoff observations can support a preregistered historical path design.
"""

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

EXPECTED_SHA256 = "b03c4e7f1cf885e9f20ea808ee538c26c21df4065b342fe04c50d09b808c344c"
REQUIRED = {
    "captured_at",
    "game_start_time",
    "event_id",
    "home_team",
    "away_team",
    "sportsbook",
    "market_type",
    "outcome",
    "price",
}
TARGET_HORIZONS_MIN = (1440, 360, 240, 120, 60, 45, 30)
LOCK_BANDS = (
    (120, 240),
    (120, 300),
    (120, 360),
)
EARLY_BANDS = (
    (1440, 1800),
    (1440, 2160),
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def qident(part: str) -> str:
    return '"' + part.replace('"', '""') + '"'


def relation_name(catalog: str, schema: str, table: str) -> str:
    # DuckDB supports catalog.schema.table; catalog can be omitted for the attached DB.
    return f"{qident(schema)}.{qident(table)}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    digest = sha256(args.db)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"archive SHA256 mismatch: {digest}")

    con = duckdb.connect(str(args.db), read_only=True)
    rels = con.execute(
        """
        select table_catalog, table_schema, table_name, table_type
        from information_schema.tables
        order by table_schema, table_name
        """
    ).fetchall()

    candidates = []
    for catalog, schema, table, table_type in rels:
        cols = {
            r[0]
            for r in con.execute(
                """
                select column_name
                from information_schema.columns
                where table_catalog=? and table_schema=? and table_name=?
                """,
                [catalog, schema, table],
            ).fetchall()
        }
        if REQUIRED.issubset(cols):
            candidates.append(
                {
                    "catalog": catalog,
                    "schema": schema,
                    "table": table,
                    "type": table_type,
                    "columns": sorted(cols),
                }
            )

    if not candidates:
        raise SystemExit("no relation satisfies Candidate 3 source contract")

    # Prefer transformed staging data if present, otherwise use the richest valid relation.
    candidates.sort(
        key=lambda x: (
            0 if x["table"] == "stg_odds" else 1,
            -len(x["columns"]),
            x["schema"],
            x["table"],
        )
    )
    selected = candidates[0]
    rel = relation_name(selected["catalog"], selected["schema"], selected["table"])

    base = f"""
        from {rel}
        where captured_at < game_start_time
          and market_type in ('h2h', 'spreads')
    """

    total_rows = con.execute(f"select count(*) {base}").fetchone()[0]
    games = con.execute(f"select count(distinct event_id) {base}").fetchone()[0]
    books = con.execute(f"select count(distinct sportsbook) {base}").fetchone()[0]
    bad_pit = con.execute(
        f"select count(*) from {rel} where captured_at >= game_start_time"
    ).fetchone()[0]
    h2h_rows = con.execute(
        f"select count(*) from {rel} where captured_at < game_start_time and market_type='h2h'"
    ).fetchone()[0]
    h2h_games = con.execute(
        f"select count(distinct event_id) from {rel} where captured_at < game_start_time and market_type='h2h'"
    ).fetchone()[0]

    # One event-level schedule frame, independent of outcome.
    game_frame_sql = f"""
        select event_id,
               min(game_start_time) as kickoff,
               min(home_team) as home_team,
               min(away_team) as away_team
        from {rel}
        where captured_at < game_start_time
        group by event_id
    """
    game_count = con.execute(f"select count(*) from ({game_frame_sql})").fetchone()[0]

    horizon = {}
    for target in TARGET_HORIZONS_MIN:
        # latest observation no later than target horizon; report age relative to target.
        rows = con.execute(
            f"""
            with g as ({game_frame_sql}),
            s as (
              select g.event_id,
                     max(o.captured_at) as selected_at,
                     g.kickoff
              from g
              left join {rel} o
                on o.event_id=g.event_id
               and o.market_type='h2h'
               and o.captured_at <= g.kickoff - interval '{target} minutes'
              group by g.event_id, g.kickoff
            )
            select
              count(*) filter (where selected_at is not null) as covered,
              median(date_diff('minute', selected_at, kickoff) - {target})
                filter (where selected_at is not null) as median_staleness_vs_target_min,
              max(date_diff('minute', selected_at, kickoff) - {target})
                filter (where selected_at is not null) as max_staleness_vs_target_min
            from s
            """
        ).fetchone()
        horizon[str(target)] = {
            "covered_games": int(rows[0] or 0),
            "coverage_rate": (rows[0] or 0) / game_count if game_count else 0.0,
            "median_staleness_vs_target_min": None if rows[1] is None else float(rows[1]),
            "max_staleness_vs_target_min": None if rows[2] is None else float(rows[2]),
        }

    lock_bands = {}
    for lo, hi in LOCK_BANDS:
        count = con.execute(
            f"""
            with g as ({game_frame_sql}),
            s as (
              select distinct g.event_id
              from g
              join {rel} o on o.event_id=g.event_id
               and o.market_type='h2h'
               and o.captured_at <= g.kickoff - interval '{lo} minutes'
               and o.captured_at >= g.kickoff - interval '{hi} minutes'
            )
            select count(*) from s
            """
        ).fetchone()[0]
        lock_bands[f"T-{hi}_to_T-{lo}"] = {
            "covered_games": int(count),
            "coverage_rate": count / game_count if game_count else 0.0,
        }

    early_bands = {}
    for lo, hi in EARLY_BANDS:
        count = con.execute(
            f"""
            with g as ({game_frame_sql}),
            s as (
              select distinct g.event_id
              from g
              join {rel} o on o.event_id=g.event_id
               and o.market_type='h2h'
               and o.captured_at <= g.kickoff - interval '{lo} minutes'
               and o.captured_at >= g.kickoff - interval '{hi} minutes'
            )
            select count(*) from s
            """
        ).fetchone()[0]
        early_bands[f"T-{hi}_to_T-{lo}"] = {
            "covered_games": int(count),
            "coverage_rate": count / game_count if game_count else 0.0,
        }

    # Require book-level overlap between an early state and the proposed lock band.
    overlap = {}
    for early_lo, early_hi in EARLY_BANDS:
        for lock_lo, lock_hi in LOCK_BANDS:
            key = f"early_T-{early_hi}_to_T-{early_lo}__lock_T-{lock_hi}_to_T-{lock_lo}"
            result = con.execute(
                f"""
                with g as ({game_frame_sql}),
                early as (
                  select g.event_id, o.sportsbook,
                         max(o.captured_at) as captured_at
                  from g join {rel} o on o.event_id=g.event_id
                  where o.market_type='h2h'
                    and o.captured_at <= g.kickoff - interval '{early_lo} minutes'
                    and o.captured_at >= g.kickoff - interval '{early_hi} minutes'
                  group by g.event_id, o.sportsbook
                ),
                lock as (
                  select g.event_id, o.sportsbook,
                         max(o.captured_at) as captured_at
                  from g join {rel} o on o.event_id=g.event_id
                  where o.market_type='h2h'
                    and o.captured_at <= g.kickoff - interval '{lock_lo} minutes'
                    and o.captured_at >= g.kickoff - interval '{lock_hi} minutes'
                  group by g.event_id, o.sportsbook
                ),
                common as (
                  select e.event_id, count(*) as common_books
                  from early e join lock l using(event_id, sportsbook)
                  group by e.event_id
                )
                select count(*) filter (where common_books>=2),
                       count(*) filter (where common_books>=5),
                       median(common_books)
                from common
                """
            ).fetchone()
            overlap[key] = {
                "games_ge_2_common_books": int(result[0] or 0),
                "games_ge_5_common_books": int(result[1] or 0),
                "median_common_books": None if result[2] is None else float(result[2]),
                "ge_5_rate_vs_all_games": (result[1] or 0) / game_count if game_count else 0.0,
            }

    report = {
        "audit_id": "LEVLINE-ADAPTIVE-C3-HISTORICAL-MARKET-PATH-SOURCE-AUDIT-V1",
        "archive": {
            "provider_repo": "bobby-king3/nfl-market-movement-tracker",
            "release": "v1.1.1",
            "asset": "nfl_odds.duckdb",
            "sha256": digest,
            "expected_sha256": EXPECTED_SHA256,
        },
        "selected_relation": selected,
        "relation_candidates": candidates,
        "counts": {
            "all_pre_match_h2h_or_spread_rows": int(total_rows),
            "distinct_games": int(games),
            "distinct_books": int(books),
            "h2h_rows": int(h2h_rows),
            "h2h_games": int(h2h_games),
            "event_schedule_games": int(game_count),
            "post_or_at_kickoff_rows_in_selected_relation": int(bad_pit),
        },
        "horizon_latest_at_or_before": horizon,
        "lock_band_coverage": lock_bands,
        "early_band_coverage": early_bands,
        "same_book_path_overlap": overlap,
        "scientific_firewall": {
            "outcomes_loaded": False,
            "fst_predictions_loaded": False,
            "completed_2026_season_outcomes_used": 0,
            "source_selection_used_target_results": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
