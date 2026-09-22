from __future__ import annotations

"""Postgame grade adapter for immutable Props 2.2 prospective receipts.

Research-only. Grades are stored separately from prospective challenger receipts so
outcomes can never contaminate or rewrite the pregame evidence. One source forecast has
one grade shared by every frozen Props 2.2 challenger derived from that source.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import nflreadpy as nfl

from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids
from nfl_forecast.props_upstream import normalize_nflverse_scramble_semantics
from research.props.v2 import grade_prospective_football_shadow as shadow_grader
from research.props.v21.evaluate_prospective_props21 import actual_player_stats
from research.props.v22.challengers import load_grid
from research.props.v22.evaluate_prospective import (
    GRADE_CONTRACT_VERSION,
    Props22EvaluationError,
    read_jsonl,
    validate_grades,
    validate_receipts,
)


class Props22GradingError(RuntimeError):
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


def _source_groups(
    receipts: Iterable[Mapping[str, Any]],
    *,
    grid: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    frozen = dict(grid or load_grid())
    expected_challengers = {
        str(item.get("id"))
        for item in frozen.get("challengers") or []
        if isinstance(item, Mapping)
    }
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        grouped[str(receipt["source_props21_forecast_sha256"])].append(receipt)

    sources: dict[str, dict[str, Any]] = {}
    for source_sha, group in grouped.items():
        challenger_ids = {str(row.get("challenger_id") or "") for row in group}
        if challenger_ids != expected_challengers:
            missing = sorted(expected_challengers - challenger_ids)
            extra = sorted(challenger_ids - expected_challengers)
            raise Props22GradingError(
                f"{source_sha}: incomplete frozen challenger set; missing={missing} extra={extra}"
            )
        identities = {
            (
                str(row.get("source_props21_forecast_id") or ""),
                str(row.get("game_id") or ""),
                str(row.get("player_id") or ""),
                str(row.get("prop_type") or ""),
                str(row.get("kickoff_utc") or ""),
            )
            for row in group
        }
        if len(identities) != 1:
            raise Props22GradingError(
                f"{source_sha}: challenger receipts disagree on source identity"
            )
        source_id, game_id, player_id, prop_type, kickoff_utc = next(iter(identities))
        if not all((source_id, game_id, player_id, prop_type, kickoff_utc)):
            raise Props22GradingError(f"{source_sha}: incomplete source identity")
        sources[source_sha] = {
            "source_props21_forecast_sha256": source_sha,
            "source_props21_forecast_id": source_id,
            "game_id": game_id,
            "player_id": player_id,
            "prop_type": prop_type,
            "kickoff_utc": kickoff_utc,
        }
    return sources


def build_grade_records(
    receipts: Iterable[Mapping[str, Any]],
    *,
    completed_games: set[str],
    outcome_pbp_games: set[str],
    actuals: Mapping[tuple[str, str, str], float],
    participation: Mapping[tuple[str, str], int],
    existing_grades: Mapping[str, Mapping[str, Any]] | None = None,
    graded_utc: datetime | None = None,
    result_source: str = "nflverse_pbp_plus_snap_participation",
    grid: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    frozen = dict(grid or load_grid())
    valid_receipts = validate_receipts(receipts, grid=frozen)
    sources = _source_groups(valid_receipts, grid=frozen)
    existing = dict(existing_grades or {})
    now = (graded_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)

    grades: list[dict[str, Any]] = []
    audit = {
        "source_forecasts": len(sources),
        "already_graded": 0,
        "not_final": 0,
        "missing_final_pbp": 0,
        "missing_participation": 0,
        "zero_offense_snaps_void": 0,
        "graded": 0,
    }

    for source_sha, source in sorted(sources.items()):
        if source_sha in existing:
            audit["already_graded"] += 1
            continue

        game_id = source["game_id"]
        player_id = source["player_id"]
        prop_type = source["prop_type"]
        if game_id not in completed_games:
            audit["not_final"] += 1
            continue
        if game_id not in outcome_pbp_games:
            audit["missing_final_pbp"] += 1
            continue

        snaps = participation.get((game_id, player_id))
        if snaps is None:
            audit["missing_participation"] += 1
            continue

        base = {
            "contract_version": GRADE_CONTRACT_VERSION,
            "source_props21_forecast_sha256": source_sha,
            "source_props21_forecast_id": source["source_props21_forecast_id"],
            "game_id": game_id,
            "player_id": player_id,
            "prop_type": prop_type,
            "finalized": True,
            "graded_utc": now.isoformat(),
            "result_source": result_source,
            "offense_snaps": int(snaps),
        }
        if int(snaps) <= 0:
            row = {
                **base,
                "grade_status": "VOID",
                "actual_result": None,
                "void_reason": "ZERO_OFFENSE_SNAPS",
            }
            audit["zero_offense_snaps_void"] += 1
        else:
            row = {
                **base,
                "grade_status": "GRADED",
                "actual_result": float(actuals.get((game_id, player_id, prop_type), 0.0)),
                "void_reason": None,
            }
            audit["graded"] += 1
        row["grade_sha256"] = _sha(row)
        grades.append(row)
    return grades, audit


def append_immutable_grades(
    path: Path,
    new_rows: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    existing_rows = read_jsonl(path)
    try:
        existing_map = validate_grades(existing_rows)
    except Props22EvaluationError as exc:
        raise Props22GradingError(str(exc)) from exc

    appended = 0
    for raw in new_rows:
        row = dict(raw)
        source_sha = str(row.get("source_props21_forecast_sha256") or "")
        grade_sha = str(row.get("grade_sha256") or "")
        unhashed = dict(row)
        unhashed.pop("grade_sha256", None)
        if len(grade_sha) != 64 or _sha(unhashed) != grade_sha:
            raise Props22GradingError("new Props 2.2 grade hash mismatch")
        prior = existing_map.get(source_sha)
        if prior is not None:
            stable_prior = dict(prior)
            stable_prior.pop("grade_sha256", None)
            stable_new = dict(row)
            stable_new.pop("grade_sha256", None)
            if _canonical(stable_prior) != _canonical(stable_new):
                raise Props22GradingError(
                    f"immutable grade conflict for source forecast {source_sha}"
                )
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical(row) + "\n")
        existing_map[source_sha] = row
        appended += 1

    return {"appended": appended, "total": len(existing_map)}


def run(
    receipts_path: Path,
    grades_path: Path,
    *,
    status_path: Path | None = None,
    allow_empty: bool = False,
) -> dict[str, Any]:
    receipts = read_jsonl(receipts_path)
    if not receipts:
        if not allow_empty:
            raise Props22GradingError(f"no Props 2.2 receipts found: {receipts_path}")
        status = {
            "contract_version": "levline-props-2.2-postgame-grade-status-v0.1",
            "status": "NO_PROSPECTIVE_RECEIPTS",
            "appended": 0,
            "total_grades": len(read_jsonl(grades_path)),
            "research_only": True,
            "production_authorized": False,
        }
        if status_path is not None:
            status_path.parent.mkdir(parents=True, exist_ok=True)
            status_path.write_text(
                json.dumps(status, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return status

    valid_receipts = validate_receipts(receipts)
    existing_rows = read_jsonl(grades_path)
    try:
        existing_grades = validate_grades(existing_rows)
    except Props22EvaluationError as exc:
        raise Props22GradingError(str(exc)) from exc

    seasons = sorted(
        {
            int(str(row["game_id"]).split("_")[0])
            for row in valid_receipts
        }
    )
    bundle = load_core_data(seasons)
    bundle = load_advanced_data(bundle, seasons)
    schedules = (
        bundle.schedules.to_pandas()
        if hasattr(bundle.schedules, "to_pandas")
        else bundle.schedules.copy()
    )
    pbp = bundle.pbp.to_pandas() if hasattr(bundle.pbp, "to_pandas") else bundle.pbp.copy()
    pbp, scramble_audit = normalize_nflverse_scramble_semantics(pbp)

    players = nfl.load_players()
    players = players.to_pandas() if hasattr(players, "to_pandas") else players.copy()
    normalized_snaps, snap_identity_audit = normalize_snap_counts_player_ids(
        bundle.snap_counts, players
    )
    if normalized_snaps is None or normalized_snaps.empty:
        raise Props22GradingError(
            f"snap identity normalization failed: {snap_identity_audit}"
        )

    completed_games = shadow_grader._completed_games(schedules)
    outcome_pbp_games, outcome_pbp_audit = shadow_grader.complete_outcome_pbp_games(pbp)
    participation, participation_audit = shadow_grader.offense_participation(
        normalized_snaps
    )
    actuals = actual_player_stats(pbp)

    new_grades, eligibility = build_grade_records(
        valid_receipts,
        completed_games=completed_games,
        outcome_pbp_games=outcome_pbp_games,
        actuals=actuals,
        participation=participation,
        existing_grades=existing_grades,
    )
    append_result = append_immutable_grades(grades_path, new_grades)
    status = {
        "contract_version": "levline-props-2.2-postgame-grade-status-v0.1",
        "status": "OK",
        "receipt_rows": len(valid_receipts),
        "eligibility": eligibility,
        "appended": append_result["appended"],
        "total_grades": append_result["total"],
        "outcome_source_audit": {
            "pbp_normalization": scramble_audit,
            "snap_identity": snap_identity_audit,
            "outcome_pbp": outcome_pbp_audit,
            "participation": participation_audit,
        },
        "research_only": True,
        "production_authorized": False,
    }
    if status_path is not None:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(
            json.dumps(status, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--receipts",
        type=Path,
        default=Path("challenger_outputs/props22/forecast_originals.jsonl"),
    )
    parser.add_argument("--grades", type=Path, required=True)
    parser.add_argument("--status", type=Path)
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    status = run(
        args.receipts,
        args.grades,
        status_path=args.status,
        allow_empty=args.allow_empty,
    )
    print(json.dumps(status, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
