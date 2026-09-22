from __future__ import annotations

"""Immutable prospective capture for preregistered Props 2.2 challengers.

This module is research-only. It consumes outcome-free Props 2.1 prospective receipts,
applies the frozen Props 2.2 transformations, and appends challenger receipts
idempotently. Existing identities may be replayed only when the receipt hash is exactly
identical; conflicting duplicates fail closed.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from research.props.v22.challengers import Props22Error, build_challenger_set, load_grid


class Props22CaptureError(RuntimeError):
    pass


CAPTURE_NOT_BEFORE_UTC = datetime(2026, 9, 22, 2, 25, 8, tzinfo=timezone.utc)

# Keep every Git blob comfortably below GitHub's 100 MiB hard file limit. This is
# transport-only sharding: receipt contents and receipt_sha256 identities are unchanged.
RECEIPT_SHARD_MAX_BYTES = 40 * 1024 * 1024
RECEIPT_SHARD_PATTERN = "part-*.jsonl"


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _jsonl_paths(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_dir():
        return sorted(item for item in path.glob(RECEIPT_SHARD_PATTERN) if item.is_file())
    if path.is_file():
        return [path]
    raise Props22CaptureError(f"{path}: unsupported receipt-store path")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for jsonl_path in _jsonl_paths(path):
        with jsonl_path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    value = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise Props22CaptureError(
                        f"{jsonl_path}:{line_no}: invalid JSON"
                    ) from exc
                if not isinstance(value, dict):
                    raise Props22CaptureError(
                        f"{jsonl_path}:{line_no}: receipt must be a JSON object"
                    )
                rows.append(value)
    return rows


def read_source_json(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise Props22CaptureError(f"{path}: source artifact must be a JSON object")
    rows = value.get("forecasts")
    if not isinstance(rows, list) or not rows:
        raise Props22CaptureError(f"{path}: source artifact requires a non-empty forecasts list")
    if not all(isinstance(row, dict) for row in rows):
        raise Props22CaptureError(f"{path}: every source forecast must be a JSON object")
    return [dict(row) for row in rows]


def _identity(row: Mapping[str, Any]) -> tuple[str, str]:
    source_sha = str(row.get("source_props21_forecast_sha256") or "").strip()
    challenger_id = str(row.get("challenger_id") or "").strip()
    if not source_sha or not challenger_id:
        raise Props22CaptureError("challenger receipt is missing immutable identity fields")
    return source_sha, challenger_id


def build_capture(
    sources: Iterable[Mapping[str, Any]],
    *,
    grid: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    frozen = dict(grid or load_grid())
    baseline = str(frozen.get("baseline_model") or "").strip()
    if not baseline:
        raise Props22CaptureError("frozen grid is missing baseline_model")

    out: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for source in sources:
        forecast_id = str(source.get("forecast_id") or "").strip()
        if not forecast_id:
            raise Props22CaptureError("Props 2.1 source receipt is missing forecast_id")
        if forecast_id in seen_source_ids:
            raise Props22CaptureError(f"duplicate source forecast_id in capture input: {forecast_id}")
        seen_source_ids.add(forecast_id)

        if source.get("outcome") is not None:
            raise Props22CaptureError(
                f"{forecast_id}: prospective capture refuses outcome-bearing source receipt"
            )
        forecast_time = _timestamp(source.get("forecast_timestamp_utc"))
        if forecast_time is None or forecast_time < CAPTURE_NOT_BEFORE_UTC:
            raise Props22CaptureError(
                f"{forecast_id}: source forecast predates Props 2.2 prospective capture boundary "
                f"{CAPTURE_NOT_BEFORE_UTC.isoformat()}"
            )
        model_version = str((source.get("provenance") or {}).get("challenger_model_version") or "")
        if model_version != baseline:
            raise Props22CaptureError(
                f"{forecast_id}: source model version {model_version!r} != frozen baseline {baseline!r}"
            )
        try:
            out.extend(build_challenger_set(source, grid=frozen))
        except Props22Error as exc:
            raise Props22CaptureError(f"{forecast_id}: {exc}") from exc

    out.sort(
        key=lambda row: (
            str(row.get("game_id") or ""),
            str(row.get("player_id") or ""),
            str(row.get("prop_type") or ""),
            str(row.get("source_props21_forecast_id") or ""),
            str(row.get("challenger_id") or ""),
        )
    )
    return out


def _receipt_line(row: Mapping[str, Any]) -> str:
    return (
        json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def _append_sharded(
    root: Path,
    rows: Iterable[Mapping[str, Any]],
    *,
    max_shard_bytes: int,
) -> None:
    if max_shard_bytes <= 0:
        raise Props22CaptureError("max_shard_bytes must be positive")
    if root.exists() and not root.is_dir():
        raise Props22CaptureError(f"{root}: sharded receipt store must be a directory")
    root.mkdir(parents=True, exist_ok=True)

    shards = _jsonl_paths(root)
    for shard in shards:
        if shard.stat().st_size > max_shard_bytes:
            raise Props22CaptureError(
                f"{shard}: existing receipt shard exceeds {max_shard_bytes} bytes"
            )

    current = shards[-1] if shards else None
    current_size = current.stat().st_size if current is not None else 0
    next_index = len(shards) + 1
    handle = None
    try:
        for row in rows:
            line = _receipt_line(row)
            line_bytes = len(line.encode("utf-8"))
            if line_bytes > max_shard_bytes:
                raise Props22CaptureError(
                    f"single receipt row exceeds shard limit: {line_bytes} > {max_shard_bytes}"
                )
            if current is None or current_size + line_bytes > max_shard_bytes:
                if handle is not None:
                    handle.close()
                current = root / f"part-{next_index:05d}.jsonl"
                if current.exists():
                    raise Props22CaptureError(f"refusing to overwrite receipt shard: {current}")
                next_index += 1
                current_size = 0
                handle = current.open("a", encoding="utf-8")
            elif handle is None:
                handle = current.open("a", encoding="utf-8")
            assert handle is not None
            handle.write(line)
            current_size += line_bytes
    finally:
        if handle is not None:
            handle.close()


def append_immutable(
    path: Path,
    rows: Iterable[Mapping[str, Any]],
    *,
    max_shard_bytes: int = RECEIPT_SHARD_MAX_BYTES,
) -> dict[str, int]:
    existing = read_jsonl(path)
    by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    for row in existing:
        ident = _identity(row)
        prior = by_identity.get(ident)
        if prior is not None and prior.get("receipt_sha256") != row.get("receipt_sha256"):
            raise Props22CaptureError(f"existing ledger has conflicting duplicate identity: {ident}")
        by_identity[ident] = row

    appended: list[Mapping[str, Any]] = []
    replayed = 0
    for row in rows:
        ident = _identity(row)
        prior = by_identity.get(ident)
        if prior is not None:
            if prior.get("receipt_sha256") != row.get("receipt_sha256"):
                raise Props22CaptureError(f"immutable challenger receipt conflict: {ident}")
            replayed += 1
            continue
        by_identity[ident] = dict(row)
        appended.append(row)

    if appended:
        if path.suffix.lower() == ".jsonl":
            # Backward-compatible single-file mode used by focused unit tests and any
            # already-materialized legacy store. Production capture uses a directory.
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                for row in appended:
                    handle.write(_receipt_line(row))
        else:
            _append_sharded(path, appended, max_shard_bytes=max_shard_bytes)
    return {"appended": len(appended), "replayed": replayed, "total": len(by_identity)}


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-receipts", type=Path)
    source.add_argument("--source-json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sources = (
        read_jsonl(args.source_receipts)
        if args.source_receipts is not None
        else read_source_json(args.source_json)
    )
    if not sources:
        raise SystemExit("source forecast input is empty")
    rows = build_capture(sources)
    result = append_immutable(args.output, rows)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
