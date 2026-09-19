from __future__ import annotations

"""Select preregistered point-in-time horizons from the prospective Props market archive."""

from dataclasses import dataclass
import argparse
import gzip
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "levline-props-v2-market-horizons-v0.1.0"


@dataclass(frozen=True)
class Horizon:
    name: str
    target_minutes: float | None
    tolerance_minutes: float | None


HORIZONS = (
    Horizon("T48H", 48.0 * 60.0, 8.0 * 60.0),
    Horizon("T24H", 24.0 * 60.0, 6.0 * 60.0),
    Horizon("T12H", 12.0 * 60.0, 4.0 * 60.0),
    Horizon("T6H", 6.0 * 60.0, 2.0 * 60.0),
    Horizon("T90M", 90.0, 30.0),
    Horizon("T30M", 30.0, 15.0),
)
NEAR_CLOSE_MAX_MINUTES = 10.0


class HorizonError(ValueError):
    pass


def has_live_source_provenance(row: Mapping[str, Any]) -> bool:
    run_id = str(row.get("source_workflow_run") or "").strip()
    generation_sha = str(row.get("source_head_sha") or "").strip().lower()
    trigger_sha = str(row.get("source_trigger_head_sha") or "").strip().lower()
    provider = str(row.get("source_market_provider") or "").strip()
    credential_mode = str(row.get("source_market_credential_mode") or "").strip()
    provenance_sha = str(row.get("source_provenance_sha256") or "").strip().lower()
    git_sha = lambda value: len(value) in {40, 64} and all(
        char in "0123456789abcdef" for char in value
    )
    sha256 = len(provenance_sha) == 64 and all(
        char in "0123456789abcdef" for char in provenance_sha
    )
    return bool(
        run_id
        and git_sha(generation_sha)
        and git_sha(trigger_sha)
        and provider
        and credential_mode
        and sha256
    )


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _load_archive_rows(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.glob("captures/*.jsonl.gz"))
    rows: list[dict[str, Any]] = []
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise HorizonError(f"{path} contains non-object row")
                if value.get("research_only") is not True or value.get("production_authorized") is not False:
                    raise HorizonError(f"{path} contains non-research market row")
                minutes = float(value.get("minutes_to_kickoff"))
                if not math.isfinite(minutes) or minutes <= 0:
                    raise HorizonError(f"{path} contains non-pregame minutes_to_kickoff")
                rows.append(value)
    return rows


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    game_id = str(row.get("game_id") or "").strip()
    player_id = str(row.get("player_id") or "").strip()
    prop_type = str(row.get("prop_type") or "").strip()
    if not game_id or not player_id or not prop_type:
        raise HorizonError("market row missing game/player/prop identity")
    return game_id, player_id, prop_type


def _select_fixed(rows: list[dict[str, Any]], horizon: Horizon) -> dict[str, Any] | None:
    assert horizon.target_minutes is not None and horizon.tolerance_minutes is not None
    eligible = []
    for row in rows:
        minutes = float(row["minutes_to_kickoff"])
        error = abs(minutes - horizon.target_minutes)
        if error <= horizon.tolerance_minutes:
            eligible.append((error, -minutes, str(row.get("captured_at_utc")), row))
    if not eligible:
        return None
    # Closest to target wins. Then prefer the earlier capture (larger minutes to kickoff),
    # then timestamp lexicographically for deterministic retry resolution.
    eligible.sort(key=lambda item: (item[0], item[1], item[2]))
    return eligible[0][3]


def _selected_record(
    row: Mapping[str, Any],
    *,
    horizon_name: str,
    target_minutes: float | None,
    tolerance_minutes: float | None,
) -> dict[str, Any]:
    artifact = row.get("market_artifact")
    if not isinstance(artifact, Mapping):
        raise HorizonError("archive row missing market_artifact")
    minutes = float(row["minutes_to_kickoff"])
    return {
        "contract_version": CONTRACT_VERSION,
        "horizon": horizon_name,
        "target_minutes_to_kickoff": target_minutes,
        "tolerance_minutes": tolerance_minutes,
        "actual_minutes_to_kickoff": minutes,
        "timing_error_minutes": (
            None if target_minutes is None else abs(minutes - float(target_minutes))
        ),
        "snapshot_id": row.get("snapshot_id"),
        "source_workflow_run": row.get("source_workflow_run"),
        "source_head_sha": row.get("source_head_sha"),
        "source_trigger_head_sha": row.get("source_trigger_head_sha"),
        "source_market_provider": row.get("source_market_provider"),
        "source_market_credential_mode": row.get("source_market_credential_mode"),
        "source_provenance_sha256": row.get("source_provenance_sha256"),
        "captured_at_utc": row.get("captured_at_utc"),
        "kickoff_utc": row.get("kickoff_utc"),
        "game_id": row.get("game_id"),
        "player_id": row.get("player_id"),
        "prop_type": row.get("prop_type"),
        "market_artifact_sha256": row.get("market_artifact_sha256"),
        "consensus_line": artifact.get("consensus_line"),
        "consensus_no_vig_p_over": artifact.get("consensus_no_vig_p_over"),
        "consensus_no_vig_p_under": artifact.get("consensus_no_vig_p_under"),
        "sportsbook_count": artifact.get("sportsbook_count"),
        "sportsbooks": artifact.get("sportsbooks"),
        "line_range": artifact.get("line_range"),
        "line_stddev": artifact.get("line_stddev"),
        "best_over_price": artifact.get("best_over_price"),
        "best_under_price": artifact.get("best_under_price"),
        "market_data_quality": artifact.get("market_data_quality"),
        "individual_books": artifact.get("individual_books"),
        "movement": artifact.get("movement"),
        "research_only": True,
        "production_authorized": False,
    }


def select_horizons(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for raw in rows:
        row = dict(raw)
        if not has_live_source_provenance(row):
            # Preserve legacy pre-amendment captures in the archive, but they are permanently
            # ineligible for prospective horizon / CLV evidence.
            continue
        if row.get("research_only") is not True or row.get("production_authorized") is not False:
            raise HorizonError("horizon selection accepts research-only rows")
        minutes = float(row.get("minutes_to_kickoff"))
        if not math.isfinite(minutes) or minutes <= 0:
            raise HorizonError("horizon selection refuses non-pregame rows")
        grouped.setdefault(_identity(row), []).append(row)

    selected: list[dict[str, Any]] = []
    for identity in sorted(grouped):
        group = grouped[identity]
        earliest = max(group, key=lambda row: (float(row["minutes_to_kickoff"]), str(row.get("captured_at_utc"))))
        selected.append(
            _selected_record(
                earliest,
                horizon_name="EARLIEST_OBSERVED",
                target_minutes=None,
                tolerance_minutes=None,
            )
        )
        for horizon in HORIZONS:
            row = _select_fixed(group, horizon)
            if row is not None:
                selected.append(
                    _selected_record(
                        row,
                        horizon_name=horizon.name,
                        target_minutes=horizon.target_minutes,
                        tolerance_minutes=horizon.tolerance_minutes,
                    )
                )
        near_close = [
            row for row in group
            if 0.0 < float(row["minutes_to_kickoff"]) <= NEAR_CLOSE_MAX_MINUTES
        ]
        if near_close:
            row = min(near_close, key=lambda value: (float(value["minutes_to_kickoff"]), str(value.get("captured_at_utc"))))
            selected.append(
                _selected_record(
                    row,
                    horizon_name="NEAR_CLOSE_OBSERVED",
                    target_minutes=0.0,
                    tolerance_minutes=NEAR_CLOSE_MAX_MINUTES,
                )
            )
    return selected


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_canon(row) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Select fixed PIT horizons from Props market archive.")
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--status", type=Path)
    args = parser.parse_args()

    rows = _load_archive_rows(args.archive_root)
    eligible_rows = [row for row in rows if has_live_source_provenance(row)]
    legacy_rows = len(rows) - len(eligible_rows)
    selected = select_horizons(eligible_rows)
    _write_jsonl(args.output, selected)
    status = {
        "contract_version": CONTRACT_VERSION,
        "archive_rows": len(rows),
        "provenance_eligible_rows": len(eligible_rows),
        "legacy_pre_provenance_rows": legacy_rows,
        "selected_rows": len(selected),
        "identities": len({_identity(row) for row in eligible_rows}) if eligible_rows else 0,
        "horizon_counts": {
            name: sum(row["horizon"] == name for row in selected)
            for name in ["EARLIEST_OBSERVED", *(h.name for h in HORIZONS), "NEAR_CLOSE_OBSERVED"]
        },
        "research_only": True,
        "production_authorized": False,
    }
    if args.status is not None:
        args.status.parent.mkdir(parents=True, exist_ok=True)
        args.status.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
