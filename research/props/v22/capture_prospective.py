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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise Props22CaptureError(f"{path}:{line_no}: invalid JSON") from exc
            if not isinstance(value, dict):
                raise Props22CaptureError(f"{path}:{line_no}: receipt must be a JSON object")
            rows.append(value)
    return rows


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


def append_immutable(path: Path, rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
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
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for row in appended:
                handle.write(
                    json.dumps(
                        row,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                        allow_nan=False,
                    )
                    + "\n"
                )
    return {"appended": len(appended), "replayed": replayed, "total": len(by_identity)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-receipts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sources = read_jsonl(args.source_receipts)
    if not sources:
        raise SystemExit("source receipt file is empty")
    rows = build_capture(sources)
    result = append_immutable(args.output, rows)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
