from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from research.sleeper_archive_capture_v1 import build_capture, capture_filename, write_capture


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source snapshot must be a JSON object")
    return payload


def _load_index(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": "levline-sleeper-player-state-index-v1", "captures": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("captures"), list):
        raise ValueError("invalid capture index")
    return payload


def capture_once(
    *,
    input_path: str,
    output_dir: str,
    index_path: str,
    source_commit_sha: str,
    source_commit_timestamp_utc: str,
    retrieval_timestamp_utc: str | None = None,
) -> dict:
    source = Path(input_path)
    if not source.exists():
        return {"status": "skipped", "reason": "missing_source_snapshot"}

    retrieval = retrieval_timestamp_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = build_capture(
        _load_json(source),
        source_commit_sha=source_commit_sha,
        source_commit_timestamp_utc=source_commit_timestamp_utc,
        retrieval_timestamp_utc=retrieval,
    )

    out_dir = Path(output_dir)
    index_file = Path(index_path)
    index = _load_index(index_file)
    prior = {str(row.get("source_commit_sha")) for row in index["captures"]}
    if source_commit_sha in prior:
        return {
            "status": "skipped",
            "reason": "source_commit_already_captured",
            "source_commit_sha": source_commit_sha,
        }

    filename = capture_filename(payload)
    target = out_dir / filename
    write_capture(target, payload)

    entry = {
        "source_commit_sha": source_commit_sha,
        "source_commit_timestamp_utc": payload["source_commit_timestamp_utc"],
        "retrieval_timestamp_utc": payload["retrieval_timestamp_utc"],
        "filename": filename,
        "content_sha256": payload["content_sha256"],
        "player_count": len(payload["players"]),
        "fields": payload["fields"],
        "field_metrics": payload["audit"]["state_fields"],
        "research_only": True,
        "production_authorized": False,
    }
    index["captures"].append(entry)
    index["captures"] = sorted(
        index["captures"],
        key=lambda row: (str(row.get("source_commit_timestamp_utc")), str(row.get("source_commit_sha"))),
    )
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "status": "captured",
        "source_commit_sha": source_commit_sha,
        "source_commit_timestamp_utc": payload["source_commit_timestamp_utc"],
        "retrieval_timestamp_utc": payload["retrieval_timestamp_utc"],
        "filename": filename,
        "player_count": len(payload["players"]),
        "field_count": len(payload["fields"]),
        "research_only": True,
        "production_changed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="research_outputs/sleeper_player_state/snapshots")
    parser.add_argument("--index", default="research_outputs/sleeper_player_state/index.json")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-commit-time", required=True)
    parser.add_argument("--retrieval-time")
    args = parser.parse_args()
    result = capture_once(
        input_path=args.input,
        output_dir=args.output_dir,
        index_path=args.index,
        source_commit_sha=args.source_commit,
        source_commit_timestamp_utc=args.source_commit_time,
        retrieval_timestamp_utc=args.retrieval_time,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
