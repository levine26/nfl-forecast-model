from __future__ import annotations

"""Prospective research-only execution of qualified inactive parsing + frozen GSIS resolution.

This module deliberately does not estimate availability, attach player value, alter forecasts,
or use the global player dictionary as a fallback resolver. It preserves real pre-kickoff
execution evidence for later scientific qualification.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research.inactive_article_player_parser_v1 import parse_inactive_article_html
from research.levline4_prospective_inactive_gsis_resolver_v1 import (
    SOURCE_PROJECTION_SHA256,
    normalize_name,
    resolve_observations,
)

CONTRACT_ID = "LEVLINE-4-2026-PROSPECTIVE-INACTIVE-EXECUTION-V1"
GLOBAL_PROJECTION_SHA256 = "023d7e5b652f56c1b41c432f394d81da60e2ab4df287daeb3baa1be76d6f2603"
SOURCE_ARCHIVE_ID = "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1"
CANDIDATE_SOURCE_KIND = "nfl_inactives_news_article"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
        rows.append(row)
    return rows


def _append_jsonl_unique(path: Path, row: dict[str, Any], *, key: str) -> None:
    existing = _read_jsonl(path)
    identity = str(row[key])
    if any(str(item.get(key)) == identity for item in existing):
        raise ValueError(f"duplicate {key}: {identity}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _latest_due_observation(archive_dir: Path) -> dict[str, Any] | None:
    rows = _read_jsonl(archive_dir / "observations.jsonl")
    eligible = [
        row
        for row in rows
        if row.get("archive_id") == SOURCE_ARCHIVE_ID and (row.get("due_games") or [])
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda row: str(row.get("captured_at_utc") or ""))


def _week_from_due_games(due_games: list[dict[str, Any]]) -> int:
    weeks: set[int] = set()
    for game in due_games:
        game_id = str(game.get("game_id") or "")
        pieces = game_id.split("_")
        if len(pieces) < 2 or pieces[0] != "2026":
            raise ValueError(f"unexpected 2026 game_id: {game_id}")
        try:
            weeks.add(int(pieces[1]))
        except ValueError as exc:
            raise ValueError(f"game_id lacks integer week: {game_id}") from exc
    if len(weeks) != 1:
        raise ValueError(f"due cohort spans multiple weeks: {sorted(weeks)}")
    week = next(iter(weeks))
    if week <= 1:
        raise ValueError("Week 1 retrospective execution is forbidden")
    return week


def _due_teams(due_games: list[dict[str, Any]]) -> set[str]:
    teams = {
        str(game.get(side) or "").strip().upper()
        for game in due_games
        for side in ("away_team", "home_team")
    }
    teams.discard("")
    if len(teams) != 2 * len(due_games):
        raise ValueError("due game cohort has missing or duplicate team identities")
    return teams


def select_matching_article(
    *,
    archive_dir: Path,
    observation: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    due_games = list(observation.get("due_games") or [])
    due_teams = _due_teams(due_games)
    captured_at = str(observation.get("captured_at_utc") or "")
    matches: list[dict[str, Any]] = []

    for source in observation.get("sources") or []:
        if source.get("source_kind") != CANDIDATE_SOURCE_KIND:
            continue
        if int(source.get("http_status", 999)) >= 400:
            continue
        relpath = str(source.get("raw_object_relpath") or "")
        raw_sha = str(source.get("raw_body_sha256") or "").lower()
        if not relpath or len(raw_sha) != 64:
            continue
        path = archive_dir / relpath
        if not path.exists():
            raise FileNotFoundError(f"captured article raw object missing: {path}")
        with gzip.open(path, "rb") as handle:
            raw = handle.read()
        if _sha256(raw) != raw_sha:
            raise RuntimeError(f"captured article SHA mismatch: {relpath}")
        parsed = parse_inactive_article_html(
            raw,
            source_url=str(source.get("url") or ""),
            captured_at_utc=captured_at,
            raw_html_sha256=raw_sha,
        )
        observed_teams = {str(row["team"]) for row in parsed.rows}
        if due_teams.issubset(observed_teams):
            matches.append(
                {
                    "source": source,
                    "raw": raw,
                    "raw_sha256": raw_sha,
                    "parsed": parsed,
                    "observed_teams": sorted(observed_teams),
                }
            )

    distinct_shas = sorted({str(item["raw_sha256"]) for item in matches})
    if not distinct_shas:
        return None, []
    if len(distinct_shas) > 1:
        raise RuntimeError(
            f"multiple distinct official article bodies match due cohort: {distinct_shas}"
        )
    same_body = [item for item in matches if item["raw_sha256"] == distinct_shas[0]]
    selected = sorted(same_body, key=lambda item: str(item["source"].get("url") or ""))[0]
    return selected, matches


def build_resolver_observations(
    *,
    cohort_rows: Iterable[dict[str, Any]],
    week: int,
    raw_sha256: str,
    source_known_by_utc: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in cohort_rows:
        team = str(row["team"]).strip().upper()
        rendered = str(row["player_name_rendered"]).strip()
        normalized = normalize_name(rendered)
        identity_payload = "|".join(
            [CONTRACT_ID, str(week), team, normalized, raw_sha256]
        ).encode("utf-8")
        observation_id = hashlib.sha256(identity_payload).hexdigest()
        if observation_id in seen:
            raise ValueError(f"duplicate prospective observation identity: {observation_id}")
        seen.add(observation_id)
        output.append(
            {
                "observation_id": observation_id,
                "week": week,
                "team": team,
                "player_name_rendered": rendered,
                "source_known_by_utc": source_known_by_utc,
                "raw_evidence_sha256": raw_sha256,
            }
        )
    return output


def build_global_display_name_index(frame: pl.DataFrame) -> dict[str, set[str]]:
    required = {"gsis_id", "display_name"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"global identity projection missing fields: {missing}")
    if any(field in frame.columns for field in ("latest_team", "status", "last_season", "jersey_number")):
        raise RuntimeError("global identity projection contains forbidden team/status semantics")
    out: dict[str, set[str]] = defaultdict(set)
    for row in frame.select(["gsis_id", "display_name"]).to_dicts():
        gsis = str(row.get("gsis_id") or "").strip()
        rendered = normalize_name(row.get("display_name"))
        if gsis and rendered:
            out[rendered].add(gsis)
    return out


def audit_resolver_rows(
    resolver_rows: Iterable[dict[str, Any]],
    *,
    global_projection_path: Path,
    expected_global_projection_sha256: str = GLOBAL_PROJECTION_SHA256,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    raw = global_projection_path.read_bytes()
    observed_sha = _sha256(raw)
    if observed_sha != expected_global_projection_sha256:
        raise RuntimeError(
            f"global identity projection sha256 mismatch: {observed_sha} != "
            f"{expected_global_projection_sha256}"
        )
    index = build_global_display_name_index(pl.read_parquet(global_projection_path))
    audited: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for resolver_row in resolver_rows:
        row = dict(resolver_row)
        normalized = str(row.get("normalized_name") or normalize_name(row.get("player_name_rendered")))
        global_candidates = sorted(index.get(normalized, set()))
        resolver_state = str(row.get("resolution_state") or "")
        resolved = row.get("resolved_gsis_id")
        if resolver_state != "RESOLVED_EXACT_UNIQUE" or not resolved:
            audit_state = "RESOLVER_NOT_RESOLVED"
        elif len(global_candidates) == 1 and global_candidates[0] == str(resolved):
            audit_state = "CROSS_SOURCE_CORROBORATED"
        elif len(global_candidates) == 1 and global_candidates[0] != str(resolved):
            audit_state = "CROSS_SOURCE_CONTRADICTION"
        else:
            audit_state = "NOT_AUDITABLE"
        counts[audit_state] += 1
        audited.append(
            {
                "schema_version": "levline-2026-prospective-inactive-cross-source-audit-v1",
                "contract_id": CONTRACT_ID,
                "observation_id": row.get("observation_id"),
                "week": row.get("week"),
                "team": row.get("team"),
                "player_name_rendered": row.get("player_name_rendered"),
                "normalized_name": normalized,
                "resolver_state": resolver_state,
                "resolver_gsis_id": resolved,
                "global_display_name_candidate_gsis_ids": global_candidates,
                "audit_state": audit_state,
                "global_source_used_as_fallback": False,
                "cross_source_corroboration_alone_qualifies_player_identity_to_gsis": False,
                "player_identity_to_gsis_qualified": False,
                "availability_probability_feature_authorized": False,
                "player_value_join_authorized": False,
                "forecast_probability_effect_authorized": False,
                "production_authorized": False,
                "completed_2026_outcomes_used": 0,
            }
        )
    return audited, dict(sorted(counts.items()))


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _copy_content_addressed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError(f"content-addressed dependency mismatch: {path}")
    if not path.exists():
        path.write_bytes(data)


def execute(
    *,
    archive_dir: Path,
    weekly_projection_path: Path,
    global_projection_path: Path,
    output_dir: Path,
    expected_weekly_projection_sha256: str = SOURCE_PROJECTION_SHA256,
    expected_global_projection_sha256: str = GLOBAL_PROJECTION_SHA256,
) -> dict[str, Any]:
    observation = _latest_due_observation(archive_dir)
    if observation is None:
        return {
            "contract_id": CONTRACT_ID,
            "status": "SKIPPED_NO_DUE_CAPTURE",
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    due_games = list(observation.get("due_games") or [])
    week = _week_from_due_games(due_games)
    due_teams = _due_teams(due_games)
    captured_at = str(observation.get("captured_at_utc") or "")
    selected, matching = select_matching_article(archive_dir=archive_dir, observation=observation)

    attempt_payload = "|".join(
        [CONTRACT_ID, captured_at, ",".join(sorted(str(g.get("game_id")) for g in due_games))]
    ).encode("utf-8")
    attempt_id = hashlib.sha256(attempt_payload).hexdigest()

    if selected is None:
        receipt = {
            "schema_version": "levline-2026-prospective-inactive-execution-v1",
            "contract_id": CONTRACT_ID,
            "attempt_id": attempt_id,
            "status": "WAITING_FOR_MATCHING_OFFICIAL_ARTICLE",
            "captured_at_utc": captured_at,
            "week": week,
            "due_game_ids": sorted(str(g.get("game_id")) for g in due_games),
            "due_teams": sorted(due_teams),
            "matching_article_bodies": 0,
            "resolver_executed": False,
            "global_audit_executed": False,
            "player_identity_to_gsis_qualified": False,
            "availability_probability_feature_authorized": False,
            "player_value_join_authorized": False,
            "forecast_probability_effect_authorized": False,
            "model_fit_authorized": False,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
        _append_jsonl_unique(output_dir / "attempts.jsonl", receipt, key="attempt_id")
        return receipt

    parsed = selected["parsed"]
    cohort_rows = [row for row in parsed.rows if str(row["team"]) in due_teams]
    observed_due_teams = {str(row["team"]) for row in cohort_rows}
    if observed_due_teams != due_teams:
        raise RuntimeError(
            f"selected article does not contain exact due-team set after filtering: "
            f"{sorted(observed_due_teams)} != {sorted(due_teams)}"
        )

    resolver_inputs = build_resolver_observations(
        cohort_rows=cohort_rows,
        week=week,
        raw_sha256=str(selected["raw_sha256"]),
        source_known_by_utc=captured_at,
    )
    resolver_rows, resolver_receipt = resolve_observations(
        resolver_inputs,
        projection_path=weekly_projection_path,
        expected_projection_sha256=expected_weekly_projection_sha256,
    )
    audit_rows, audit_counts = audit_resolver_rows(
        resolver_rows,
        global_projection_path=global_projection_path,
        expected_global_projection_sha256=expected_global_projection_sha256,
    )
    contradictions = int(audit_counts.get("CROSS_SOURCE_CONTRADICTION", 0))
    execution_id_payload = "|".join(
        [CONTRACT_ID, captured_at, str(selected["raw_sha256"]), str(week)]
    ).encode("utf-8")
    execution_id = hashlib.sha256(execution_id_payload).hexdigest()
    run_dir = output_dir / "executions" / execution_id

    _write_jsonl(run_dir / "parsed_due_cohort.jsonl", cohort_rows)
    _write_jsonl(run_dir / "resolver_inputs.jsonl", resolver_inputs)
    _write_jsonl(run_dir / "resolver_rows.jsonl", resolver_rows)
    _write_jsonl(run_dir / "cross_source_audit_rows.jsonl", audit_rows)

    weekly_bytes = weekly_projection_path.read_bytes()
    global_bytes = global_projection_path.read_bytes()
    weekly_sha = _sha256(weekly_bytes)
    global_sha = _sha256(global_bytes)
    _copy_content_addressed(
        output_dir / "dependencies" / f"weekly-identity-{weekly_sha}.parquet", weekly_bytes
    )
    _copy_content_addressed(
        output_dir / "dependencies" / f"global-identity-{global_sha}.parquet", global_bytes
    )

    receipt = {
        "schema_version": "levline-2026-prospective-inactive-execution-v1",
        "contract_id": CONTRACT_ID,
        "attempt_id": attempt_id,
        "execution_id": execution_id,
        "status": "FAIL_CROSS_SOURCE_CONTRADICTION" if contradictions else "PASS_EVIDENCE_CAPTURED",
        "captured_at_utc": captured_at,
        "week": week,
        "due_game_ids": sorted(str(g.get("game_id")) for g in due_games),
        "due_teams": sorted(due_teams),
        "selected_source_url": str(selected["source"].get("url") or ""),
        "selected_raw_html_sha256": str(selected["raw_sha256"]),
        "matching_article_records": len(matching),
        "matching_distinct_article_bodies": 1,
        "full_article_team_sections": int(parsed.audit["team_sections"]),
        "full_article_inactive_entries": int(parsed.audit["inactive_entries"]),
        "due_cohort_team_sections": len(observed_due_teams),
        "due_cohort_inactive_entries": len(cohort_rows),
        "weekly_identity_projection_sha256": weekly_sha,
        "global_identity_projection_sha256": global_sha,
        "resolver_receipt": resolver_receipt,
        "cross_source_audit_counts": audit_counts,
        "cross_source_contradictions": contradictions,
        "global_source_used_as_fallback": False,
        "real_execution_is_self_qualifying": False,
        "player_identity_to_gsis_qualified": False,
        "game_day_membership_qualified": False,
        "availability_probability_feature_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    (run_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _append_jsonl_unique(output_dir / "attempts.jsonl", receipt, key="attempt_id")
    return receipt


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=Path("research_outputs/inactive_article_source_archive_v1"),
    )
    parser.add_argument("--weekly-projection", type=Path, required=True)
    parser.add_argument("--global-projection", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs/levline4_prospective_inactive_execution_v1"),
    )
    args = parser.parse_args()
    receipt = execute(
        archive_dir=args.archive_dir,
        weekly_projection_path=args.weekly_projection,
        global_projection_path=args.global_projection,
        output_dir=args.output_dir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt.get("status") == "FAIL_CROSS_SOURCE_CONTRADICTION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
