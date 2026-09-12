from __future__ import annotations

"""Audit historical weekly-roster source coverage for the V09B positive-class denominator.

This is a source diagnostic only. It does not define eligible statuses, construct active or
inactive labels, use postgame participation, or fit a model.
"""

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import nflreadpy as nfl
import polars as pl
import requests

EXPECTED_GAMES = {
    2012: 256,
    2013: 256,
    2014: 256,
    2015: 256,
    2016: 256,
    2017: 256,
    2018: 256,
    2019: 256,
    2020: 256,
    2021: 272,
}
EXPECTED_TEAM_GAME_WEEKS = {season: games * 2 for season, games in EXPECTED_GAMES.items()}
REQUIRED_FIELDS = {
    "season",
    "game_type",
    "week",
    "team",
    "gsis_id",
    "status_description_abbr",
}
OPTIONAL_FIELDS = {"status_short_description"}
RELEASE_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/"
    "roster_weekly_{season}.parquet"
)

TEAM_ALIASES = {
    "JAC": "JAX",
    "SD": "LAC",
    "STL": "LA",
    "LAR": "LA",
    "OAK": "LV",
    "WSH": "WAS",
}


def normalize_team(value: object) -> str:
    team = str(value or "").strip().upper()
    return TEAM_ALIASES.get(team, team)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def normalized_row_digest(frame: pl.DataFrame) -> str:
    rows = []
    for row in frame.to_dicts():
        normalized = {str(key): _jsonable(value) for key, value in row.items()}
        rows.append(json.dumps(normalized, sort_keys=True, separators=(",", ":")))
    rows.sort()
    return _sha256(("\n".join(rows) + ("\n" if rows else "")).encode("utf-8"))


def canonical_games(season: int) -> list[dict[str, object]]:
    frame = nfl.load_schedules(seasons=[season])
    rows = frame.to_dicts() if hasattr(frame, "to_dicts") else frame.to_pandas().to_dict("records")
    games = [row for row in rows if str(row.get("game_type")) == "REG"]
    games.sort(key=lambda row: (int(row["week"]), str(row["game_id"])))
    expected = EXPECTED_GAMES[season]
    if len(games) != expected:
        raise RuntimeError(f"canonical schedule count mismatch for {season}: {len(games)} != {expected}")
    return games


def canonical_team_game_weeks(games: list[dict[str, object]]) -> set[tuple[int, str]]:
    keys: set[tuple[int, str]] = set()
    for game in games:
        week = int(game["week"])
        keys.add((week, normalize_team(game["away_team"])))
        keys.add((week, normalize_team(game["home_team"])))
    return keys


def source_era(season: int) -> str:
    return "data_exchange_2012_2015" if season <= 2015 else "ngs_2016_2021"


def _status_distribution(frame: pl.DataFrame, column: str) -> dict[str, int] | None:
    if column not in frame.columns:
        return None
    values = ["<NULL>" if value is None else str(value) for value in frame[column].to_list()]
    return dict(sorted(Counter(values).items()))


def audit_frame(
    *,
    season: int,
    frame: pl.DataFrame,
    games: list[dict[str, object]],
    raw_sha256: str,
    raw_size_bytes: int,
    parquet_magic_valid: bool,
    source_url: str,
) -> dict[str, Any]:
    if season not in EXPECTED_GAMES:
        raise ValueError(f"unsupported season: {season}")

    missing_fields = sorted(REQUIRED_FIELDS - set(frame.columns))
    if missing_fields:
        return {
            "audit_version": 1,
            "season": season,
            "source_era": source_era(season),
            "source_url": source_url,
            "raw_parquet_sha256": raw_sha256,
            "raw_size_bytes": raw_size_bytes,
            "parquet_magic_valid": parquet_magic_valid,
            "required_fields_present": False,
            "missing_required_fields": missing_fields,
            "all_frozen_gates_pass": False,
            "game_day_roster_universe_qualified": False,
            "source_era_status_semantics_qualified": False,
            "v09b_model_fit_authorized": False,
            "model_fit_performed": False,
            "game_outcomes_used": 0,
            "completed_2026_outcomes_used": 0,
        }

    season_frame = frame.filter(
        (pl.col("season").cast(pl.Int64, strict=False) == season)
        & (pl.col("game_type").cast(pl.Utf8, strict=False) == "REG")
    )
    rows = season_frame.to_dicts()
    canonical_keys = canonical_team_game_weeks(games)
    expected_keys = EXPECTED_TEAM_GAME_WEEKS[season]
    if len(canonical_keys) != expected_keys:
        raise RuntimeError(
            f"canonical team-game-week count mismatch for {season}: "
            f"{len(canonical_keys)} != {expected_keys}"
        )

    source_counts: Counter[tuple[int, str]] = Counter()
    duplicate_identity_counts: Counter[tuple[int, str, str]] = Counter()
    missing_gsis = 0
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = normalize_team(row.get("team"))
        if not team:
            continue
        key = (week, team)
        source_counts[key] += 1
        gsis_raw = row.get("gsis_id")
        gsis = "" if gsis_raw is None else str(gsis_raw).strip()
        if not gsis:
            missing_gsis += 1
        else:
            duplicate_identity_counts[(week, team, gsis)] += 1
        normalized_rows.append({
            "season": season,
            "week": week,
            "team": team,
            "gsis_id": gsis or None,
            "status_description_abbr": _jsonable(row.get("status_description_abbr")),
            "status_short_description": _jsonable(row.get("status_short_description"))
            if "status_short_description" in frame.columns
            else None,
        })

    source_keys = set(source_counts)
    missing_keys = sorted(canonical_keys - source_keys)
    extra_keys = sorted(source_keys - canonical_keys)
    covered = len(canonical_keys) - len(missing_keys)
    coverage_rate = covered / len(canonical_keys) if canonical_keys else 0.0
    duplicates = {
        f"{season}-W{week}-{team}-{gsis}": count
        for (week, team, gsis), count in sorted(duplicate_identity_counts.items())
        if count > 1
    }
    canonical_row_counts = [source_counts[key] for key in sorted(canonical_keys)]
    normalized_payload = "\n".join(
        sorted(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in normalized_rows)
    )
    normalized_digest = _sha256(
        (normalized_payload + ("\n" if normalized_payload else "")).encode("utf-8")
    )

    frozen_pass = bool(
        parquet_magic_valid
        and len(raw_sha256) == 64
        and not missing_fields
        and len(games) == EXPECTED_GAMES[season]
        and len(canonical_keys) == expected_keys
        and coverage_rate == 1.0
        and not duplicates
    )

    return {
        "audit_version": 1,
        "season": season,
        "source_era": source_era(season),
        "source_url": source_url,
        "raw_parquet_sha256": raw_sha256,
        "raw_size_bytes": raw_size_bytes,
        "parquet_magic_valid": parquet_magic_valid,
        "release_normalized_row_sha256": normalized_row_digest(frame),
        "canonical_filtered_row_sha256": normalized_digest,
        "required_fields_present": True,
        "missing_required_fields": [],
        "optional_fields_present": sorted(OPTIONAL_FIELDS & set(frame.columns)),
        "generic_status_field_present": "status" in frame.columns,
        "generic_status_used_for_audit_membership": False,
        "canonical_games": len(games),
        "expected_games": EXPECTED_GAMES[season],
        "canonical_team_game_weeks": len(canonical_keys),
        "expected_team_game_weeks": expected_keys,
        "covered_canonical_team_game_weeks": covered,
        "canonical_team_game_week_coverage_rate": coverage_rate,
        "missing_canonical_team_game_weeks": [
            {"week": week, "team": team} for week, team in missing_keys
        ],
        "source_team_game_weeks_outside_canonical_schedule": [
            {"week": week, "team": team, "rows": source_counts[(week, team)]}
            for week, team in extra_keys
        ],
        "canonical_team_game_week_row_count_min": min(canonical_row_counts)
        if canonical_row_counts
        else 0,
        "canonical_team_game_week_row_count_max": max(canonical_row_counts)
        if canonical_row_counts
        else 0,
        "canonical_filtered_rows": sum(canonical_row_counts),
        "season_reg_rows_total": len(rows),
        "missing_gsis_id_rows": missing_gsis,
        "missing_gsis_id_rate": missing_gsis / len(rows) if rows else 0.0,
        "duplicate_non_null_gsis_player_team_week_keys": len(duplicates),
        "duplicate_non_null_gsis_player_team_week_examples": dict(list(duplicates.items())[:50]),
        "status_description_abbr_distribution": _status_distribution(
            season_frame, "status_description_abbr"
        ),
        "status_short_description_distribution": _status_distribution(
            season_frame, "status_short_description"
        ),
        "all_frozen_gates_pass": frozen_pass,
        "weekly_roster_raw_source_coverage_qualified": frozen_pass,
        "source_era_status_semantics_qualified": False,
        "game_day_roster_universe_qualified": False,
        "player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def fetch_release(season: int, *, timeout: float = 60.0) -> tuple[bytes, str]:
    url = RELEASE_URL.format(season=season)
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; LevLine4Research/1.0; source-audit)"},
    )
    response.raise_for_status()
    return bytes(response.content), url


def audit_season(season: int, *, timeout: float = 60.0) -> dict[str, Any]:
    raw, url = fetch_release(season, timeout=timeout)
    parquet_magic = len(raw) >= 8 and raw[:4] == b"PAR1" and raw[-4:] == b"PAR1"
    frame = pl.read_parquet(io.BytesIO(raw))
    games = canonical_games(season)
    return audit_frame(
        season=season,
        frame=frame,
        games=games,
        raw_sha256=_sha256(raw),
        raw_size_bytes=len(raw),
        parquet_magic_valid=parquet_magic,
        source_url=url,
    )


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(EXPECTED_GAMES))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.season, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["all_frozen_gates_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
