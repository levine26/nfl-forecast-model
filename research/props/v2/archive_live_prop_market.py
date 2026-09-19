from __future__ import annotations

"""Archive normalized multi-book player-prop market snapshots from live audit artifacts.

This research layer consumes already-captured live Props artifacts. It makes no sportsbook
requests, changes no production forecast, and preserves no API credential. Each accepted snapshot
must be pregame, research-only, and production-unauthorized.
"""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

CONTRACT_VERSION = "levline-props-v2-market-archive-v0.1.0"


class MarketArchiveError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git_sha(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) not in {40, 64} or any(char not in "0123456789abcdef" for char in text):
        raise MarketArchiveError("source_head_sha must be a git SHA")
    return text


def _dt(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise MarketArchiveError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise MarketArchiveError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise MarketArchiveError("manifest rows must be objects")
        rows.append(value)
    return rows


def _append_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(_canon(row) + "\n")


def _load_snapshot(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MarketArchiveError(f"{path} must contain a JSON object")
    if value.get("research_only") is not True:
        raise MarketArchiveError(f"{path} is not research-only")
    if value.get("production_authorized") is not False:
        raise MarketArchiveError(f"{path} is production-authorized")
    artifacts = value.get("market_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise MarketArchiveError(f"{path} has no market_artifacts")
    if not all(isinstance(row, dict) for row in artifacts):
        raise MarketArchiveError(f"{path} market_artifacts must be objects")
    return value


def _kickoffs(snapshot: Mapping[str, Any]) -> dict[str, datetime]:
    audit = snapshot.get("audit")
    if not isinstance(audit, Mapping):
        raise MarketArchiveError("snapshot missing audit")
    matched = audit.get("matched_events")
    if not isinstance(matched, list) or not matched:
        raise MarketArchiveError("snapshot missing matched_events")
    out: dict[str, datetime] = {}
    for row in matched:
        if not isinstance(row, Mapping):
            raise MarketArchiveError("matched event must be an object")
        game_id = str(row.get("game_id") or "").strip()
        if not game_id:
            raise MarketArchiveError("matched event missing game_id")
        kickoff = _dt(row.get("kickoff_utc"))
        if game_id in out and out[game_id] != kickoff:
            raise MarketArchiveError(f"conflicting kickoff for {game_id}")
        out[game_id] = kickoff
    return out


def _raw_payload_sha(market_path: Path) -> str | None:
    raw = market_path.with_name("market.raw.json")
    if not raw.exists():
        return None
    value = json.loads(raw.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        return None
    digest = value.get("payload_sha256")
    return str(digest) if digest else None


def _write_gzip_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    payload = "".join(_canon(row) + "\n" for row in rows).encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
            zipped.write(payload)


def archive_snapshot(
    market_path: Path,
    *,
    output_dir: Path,
    manifest_path: Path,
    source_workflow_run: str,
    source_head_sha: str,
) -> dict[str, Any]:
    source_run = str(source_workflow_run or "").strip()
    if not source_run:
        raise MarketArchiveError("source_workflow_run is required")
    source_sha = _git_sha(source_head_sha)
    snapshot = _load_snapshot(market_path)
    captured = _dt(snapshot.get("captured_at_utc"))
    kickoffs = _kickoffs(snapshot)
    canonical = _canon(snapshot)
    snapshot_sha = _sha_text(canonical)
    snapshot_id = "props_market_" + snapshot_sha[:24]

    existing = _read_manifest(manifest_path)
    by_id = {
        str(row.get("snapshot_id")): row
        for row in existing
        if isinstance(row, dict) and row.get("snapshot_id")
    }
    if snapshot_id in by_id:
        return {
            "snapshot_id": snapshot_id,
            "status": "existing",
            "artifact_count": int(by_id[snapshot_id].get("artifact_count", 0)),
        }

    rows: list[dict[str, Any]] = []
    for artifact in snapshot["market_artifacts"]:
        game_id = str(artifact.get("game_id") or "").strip()
        if game_id not in kickoffs:
            raise MarketArchiveError(f"market artifact has unknown game_id {game_id!r}")
        kickoff = kickoffs[game_id]
        if captured >= kickoff:
            raise MarketArchiveError(
                f"refusing post-kickoff market snapshot for {game_id}: {captured.isoformat()}"
            )
        minutes_to_kickoff = (kickoff - captured).total_seconds() / 60.0
        rows.append(
            {
                "contract_version": CONTRACT_VERSION,
                "snapshot_id": snapshot_id,
                "source_workflow_run": source_run,
                "source_head_sha": source_sha,
                "captured_at_utc": captured.isoformat(),
                "kickoff_utc": kickoff.isoformat(),
                "minutes_to_kickoff": minutes_to_kickoff,
                "game_id": game_id,
                "player_id": artifact.get("player_id"),
                "prop_type": artifact.get("prop_type"),
                "market_artifact_sha256": _sha_text(_canon(artifact)),
                "market_artifact": artifact,
                "research_only": True,
                "production_authorized": False,
            }
        )

    stamp = captured.strftime("%Y%m%dT%H%M%SZ")
    archive_rel = Path("captures") / f"{stamp}_{snapshot_id}.jsonl.gz"
    archive_path = output_dir / archive_rel
    _write_gzip_jsonl(archive_path, rows)

    raw_sha = _raw_payload_sha(market_path)
    manifest_row = {
        "contract_version": CONTRACT_VERSION,
        "snapshot_id": snapshot_id,
        "captured_at_utc": captured.isoformat(),
        "source_workflow_run": source_run,
        "source_head_sha": source_sha,
        "normalized_snapshot_sha256": snapshot_sha,
        "raw_provider_payload_sha256": raw_sha,
        "artifact_count": len(rows),
        "game_count": len({row["game_id"] for row in rows}),
        "min_minutes_to_kickoff": min(row["minutes_to_kickoff"] for row in rows),
        "max_minutes_to_kickoff": max(row["minutes_to_kickoff"] for row in rows),
        "archive_file": str(archive_rel).replace("\\", "/"),
        "research_only": True,
        "production_authorized": False,
    }
    _append_manifest(manifest_path, [manifest_row])
    return {"snapshot_id": snapshot_id, "status": "archived", **manifest_row}


def archive_artifact_root(
    artifact_root: Path,
    *,
    output_dir: Path,
    manifest_path: Path,
    source_workflow_run: str,
    source_head_sha: str,
) -> dict[str, Any]:
    source_run = str(source_workflow_run or "").strip()
    if not source_run:
        raise MarketArchiveError("source_workflow_run is required")
    source_sha = _git_sha(source_head_sha)
    market_paths = sorted(artifact_root.rglob("market.json"))
    if not market_paths:
        raise MarketArchiveError(f"no market.json found under {artifact_root}")
    results = [
        archive_snapshot(
            path,
            output_dir=output_dir,
            manifest_path=manifest_path,
            source_workflow_run=source_run,
            source_head_sha=source_sha,
        )
        for path in market_paths
    ]
    return {
        "contract_version": CONTRACT_VERSION,
        "source_workflow_run": source_run,
        "source_head_sha": source_sha,
        "snapshot_files_found": len(market_paths),
        "archived": sum(row["status"] == "archived" for row in results),
        "existing": sum(row["status"] == "existing" for row in results),
        "results": results,
        "research_only": True,
        "production_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive live Props market audit snapshots.")
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-workflow-run", required=True)
    parser.add_argument("--source-head-sha", required=True)
    parser.add_argument("--status", type=Path)
    args = parser.parse_args()

    result = archive_artifact_root(
        args.artifact_root,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        source_workflow_run=args.source_workflow_run,
        source_head_sha=args.source_head_sha,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.status is not None:
        args.status.parent.mkdir(parents=True, exist_ok=True)
        args.status.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
