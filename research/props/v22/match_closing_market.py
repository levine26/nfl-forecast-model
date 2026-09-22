from __future__ import annotations

"""Prospective closing-market matcher for frozen Props 2.2 receipts.

Research-only. This module never reads outcomes, never mutates forecast receipts, and never
requests sportsbook data. It matches immutable Props 2.2 source forecasts to the append-only
Props market archive, selecting the latest exact-identity capture at/after forecast time and
strictly before kickoff. Closing events are append-only and keyed to the immutable source
Props 2.1 forecast SHA.
"""

from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "levline-props-2.2-closing-market-v0.1"
ARCHIVE_CONTRACT_VERSION = "levline-props-v2-market-archive-v0.1.0"
CAPTURE_NOT_BEFORE_UTC = datetime(2026, 9, 22, 2, 25, 8, tzinfo=timezone.utc)
ARCHIVE_SETTLEMENT_GRACE = timedelta(minutes=60)
ORIGINAL_PROBABILITY_TOLERANCE = 1e-6
LINE_TOLERANCE = 1e-9
BINARY_TD_MARKETS = {"rushing_td", "receiving_td", "anytime_td"}

LIVE_PROVENANCE_FIELDS = (
    "source_trigger_head_sha",
    "source_market_provider",
    "source_market_credential_mode",
    "source_provenance_sha256",
)


class ClosingMarketError(RuntimeError):
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


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _timestamp(value: Any, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ClosingMarketError(f"invalid {label}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ClosingMarketError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _jsonl_paths(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_dir():
        return sorted(item for item in path.glob("part-*.jsonl") if item.is_file())
    if path.is_file():
        return [path]
    raise ClosingMarketError(f"{path}: unsupported JSONL store path")


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
                    raise ClosingMarketError(
                        f"{jsonl_path}:{line_no}: invalid JSON"
                    ) from exc
                if not isinstance(value, dict):
                    raise ClosingMarketError(
                        f"{jsonl_path}:{line_no}: row must be a JSON object"
                    )
                rows.append(value)
    return rows


def load_archive_rows(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    value = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ClosingMarketError(f"{path}:{line_no}: invalid JSON") from exc
                if not isinstance(value, dict):
                    raise ClosingMarketError(f"{path}:{line_no}: archive row must be an object")
                rows.append(value)
    return rows


def _has_live_provenance(row: Mapping[str, Any]) -> bool:
    present = [bool(str(row.get(field) or "").strip()) for field in LIVE_PROVENANCE_FIELDS]
    if any(present) and not all(present):
        raise ClosingMarketError("archive row has partial live-source provenance")
    return all(present)


def _validate_archive_row(row: Mapping[str, Any]) -> None:
    if row.get("contract_version") != ARCHIVE_CONTRACT_VERSION:
        raise ClosingMarketError("unexpected market archive contract")
    if row.get("research_only") is not True or row.get("production_authorized") is not False:
        raise ClosingMarketError("closing matcher accepts research-only archive rows")
    captured = _timestamp(row.get("captured_at_utc"), label="archive captured_at_utc")
    kickoff = _timestamp(row.get("kickoff_utc"), label="archive kickoff_utc")
    minutes = _num(row.get("minutes_to_kickoff"))
    if captured >= kickoff or minutes is None or minutes <= 0:
        raise ClosingMarketError("market archive contains non-pregame row")
    if not str(row.get("game_id") or "").strip():
        raise ClosingMarketError("archive row missing game_id")
    if not str(row.get("player_id") or "").strip():
        raise ClosingMarketError("archive row missing player_id")
    if not str(row.get("prop_type") or "").strip():
        raise ClosingMarketError("archive row missing prop_type")
    artifact = row.get("market_artifact")
    if not isinstance(artifact, Mapping):
        raise ClosingMarketError("archive row missing market_artifact")


def _source_signature(row: Mapping[str, Any]) -> tuple[Any, ...]:
    line = row.get("line") if isinstance(row.get("line"), Mapping) else {}
    probability = row.get("probability") if isinstance(row.get("probability"), Mapping) else {}
    chronology = row.get("chronology") if isinstance(row.get("chronology"), Mapping) else {}
    return (
        str(row.get("source_props21_forecast_id") or ""),
        str(row.get("game_id") or ""),
        str(row.get("player_id") or ""),
        str(row.get("prop_type") or ""),
        str(row.get("kickoff_utc") or ""),
        str(row.get("forecast_timestamp_utc") or ""),
        str(chronology.get("market_capture_utc") or ""),
        _num(line.get("market_line")),
        _num(probability.get("market_probability")),
        _num(probability.get("model_probability")),
        str(probability.get("kind") or ""),
    )


def collapse_source_forecasts(
    receipts: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in receipts:
        if row.get("outcome") is not None:
            raise ClosingMarketError("closing matcher refuses outcome-bearing forecast receipts")
        if row.get("research_only") is not True or row.get("production_authorized") is not False:
            raise ClosingMarketError("Props 2.2 closing matcher accepts research-only receipts")
        source_sha = str(row.get("source_props21_forecast_sha256") or "").strip()
        if not source_sha:
            raise ClosingMarketError("Props 2.2 receipt missing source forecast SHA")
        grouped.setdefault(source_sha, []).append(row)

    sources: list[dict[str, Any]] = []
    for source_sha, group in sorted(grouped.items()):
        signatures = {_source_signature(row) for row in group}
        if len(signatures) != 1:
            raise ClosingMarketError(f"conflicting Props 2.2 source identity: {source_sha}")
        first = group[0]
        signature = next(iter(signatures))
        (
            source_id,
            game_id,
            player_id,
            prop_type,
            kickoff_text,
            forecast_text,
            market_capture_text,
            original_line,
            original_market_probability,
            model_probability,
            probability_kind,
        ) = signature
        if not all((source_id, game_id, player_id, prop_type, kickoff_text, forecast_text)):
            raise ClosingMarketError(f"incomplete source identity: {source_sha}")
        forecast = _timestamp(forecast_text, label="forecast_timestamp_utc")
        kickoff = _timestamp(kickoff_text, label="kickoff_utc")
        if forecast < CAPTURE_NOT_BEFORE_UTC:
            raise ClosingMarketError(
                f"{source_sha}: source forecast predates Props 2.2 prospective boundary"
            )
        if forecast >= kickoff:
            raise ClosingMarketError(f"{source_sha}: source forecast is not pregame")
        market_capture = (
            _timestamp(market_capture_text, label="market_capture_utc")
            if market_capture_text
            else None
        )
        if market_capture is not None and market_capture > forecast:
            raise ClosingMarketError(f"{source_sha}: original market capture is post-forecast")
        sources.append(
            {
                "source_sha": source_sha,
                "source_id": source_id,
                "game_id": game_id,
                "player_id": player_id,
                "prop_type": prop_type,
                "kickoff": kickoff,
                "forecast": forecast,
                "market_capture": market_capture,
                "original_line": original_line,
                "original_market_probability": original_market_probability,
                "model_probability": model_probability,
                "probability_kind": probability_kind,
            }
        )
    return sources


def _archive_identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("game_id") or ""),
        str(row.get("player_id") or ""),
        str(row.get("prop_type") or ""),
    )


def _source_identity(source: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(source["game_id"]),
        str(source["player_id"]),
        str(source["prop_type"]),
    )


def _event_probability(artifact: Mapping[str, Any], kind: str) -> float | None:
    if kind == "over":
        return _num(artifact.get("consensus_no_vig_p_over"))
    if kind == "td":
        value = _num(artifact.get("consensus_no_vig_probability"))
        if value is None:
            value = _num(artifact.get("consensus_no_vig_p_over"))
        return value
    return None


def _side_probability(artifact: Mapping[str, Any], side: str, kind: str) -> float | None:
    if kind == "over":
        over = _num(artifact.get("consensus_no_vig_p_over"))
        under = _num(artifact.get("consensus_no_vig_p_under"))
        if side == "over":
            return over
        if side == "under":
            return under if under is not None else (1.0 - over if over is not None else None)
    if kind == "td":
        yes = _event_probability(artifact, kind)
        no = _num(artifact.get("consensus_no_vig_p_under"))
        if side == "yes":
            return yes
        if side == "no":
            return no if no is not None else (1.0 - yes if yes is not None else None)
    return None


def _same_line(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= LINE_TOLERANCE


def _model_side(source: Mapping[str, Any]) -> str | None:
    probability = _num(source.get("model_probability"))
    kind = str(source.get("probability_kind") or "")
    if probability is None:
        return None
    if kind == "over":
        return "over" if probability >= 0.5 else "under"
    if kind == "td":
        return "yes" if probability >= 0.5 else "no"
    return None


def select_closing_row(
    source: Mapping[str, Any],
    archive_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any] | None:
    forecast = source["forecast"]
    kickoff = source["kickoff"]
    candidates: list[dict[str, Any]] = []
    for raw in archive_rows:
        row = dict(raw)
        _validate_archive_row(row)
        if not _has_live_provenance(row):
            continue
        if _archive_identity(row) != _source_identity(source):
            continue
        row_kickoff = _timestamp(row.get("kickoff_utc"), label="archive kickoff_utc")
        if row_kickoff != kickoff:
            raise ClosingMarketError(
                f"kickoff mismatch for exact market identity {_source_identity(source)}"
            )
        captured = _timestamp(row.get("captured_at_utc"), label="archive captured_at_utc")
        if forecast <= captured < kickoff:
            candidates.append(row)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (
            _timestamp(row.get("captured_at_utc"), label="archive captured_at_utc"),
            str(row.get("snapshot_id") or ""),
            str(row.get("market_artifact_sha256") or ""),
        ),
    )


def select_original_price_basis(
    source: Mapping[str, Any],
    archive_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any] | None:
    forecast = source["forecast"]
    kickoff = source["kickoff"]
    original_line = _num(source.get("original_line"))
    original_probability = _num(source.get("original_market_probability"))
    kind = str(source.get("probability_kind") or "")
    candidates: list[dict[str, Any]] = []
    for raw in archive_rows:
        row = dict(raw)
        _validate_archive_row(row)
        if not _has_live_provenance(row):
            continue
        if _archive_identity(row) != _source_identity(source):
            continue
        row_kickoff = _timestamp(row.get("kickoff_utc"), label="archive kickoff_utc")
        if row_kickoff != kickoff:
            raise ClosingMarketError(
                f"kickoff mismatch for exact market identity {_source_identity(source)}"
            )
        captured = _timestamp(row.get("captured_at_utc"), label="archive captured_at_utc")
        if captured > forecast:
            continue
        artifact = row["market_artifact"]
        if kind == "over" and original_line is not None:
            if not _same_line(_num(artifact.get("consensus_line")), original_line):
                continue
        archived_probability = _event_probability(artifact, kind)
        if (
            original_probability is not None
            and archived_probability is not None
            and abs(original_probability - archived_probability) > ORIGINAL_PROBABILITY_TOLERANCE
        ):
            continue
        candidates.append(row)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (
            _timestamp(row.get("captured_at_utc"), label="archive captured_at_utc"),
            str(row.get("snapshot_id") or ""),
            str(row.get("market_artifact_sha256") or ""),
        ),
    )


def _american_to_decimal(value: Any) -> float | None:
    odds = _num(value)
    if odds is None or odds == 0:
        return None
    if odds > 0:
        return 1.0 + odds / 100.0
    return 1.0 + 100.0 / abs(odds)


def _american_to_implied(value: Any) -> float | None:
    decimal = _american_to_decimal(value)
    if decimal is None or decimal <= 1.0:
        return None
    return 1.0 / decimal


def _price_value(book: Mapping[str, Any], side: str) -> float | None:
    for key in (
        f"{side}_american",
        f"{side}_price_american",
        f"{side}_price",
    ):
        value = _num(book.get(key))
        if value is not None:
            return value
    return None


def _best_exact_threshold_price(
    artifact: Mapping[str, Any],
    *,
    side: str,
    threshold: float | None,
    binary: bool,
) -> dict[str, Any] | None:
    books = artifact.get("individual_books")
    if not isinstance(books, list):
        return None
    candidates: list[dict[str, Any]] = []
    for raw in books:
        if not isinstance(raw, Mapping):
            continue
        if not binary:
            line = _num(raw.get("line"))
            if threshold is None or not _same_line(line, threshold):
                continue
        american = _price_value(raw, side)
        decimal = _american_to_decimal(american)
        implied = _american_to_implied(american)
        if american is None or decimal is None or implied is None:
            continue
        candidates.append(
            {
                "sportsbook": str(
                    raw.get("sportsbook_key")
                    or raw.get("sportsbook")
                    or raw.get("book")
                    or ""
                ),
                "american": american,
                "decimal": decimal,
                "implied_probability": implied,
                "line": _num(raw.get("line")),
            }
        )
    if not candidates:
        return None
    return max(candidates, key=lambda row: (float(row["decimal"]), row["sportsbook"]))


def _archive_provenance(row: Mapping[str, Any]) -> dict[str, Any]:
    artifact = row["market_artifact"]
    return {
        "snapshot_id": row.get("snapshot_id"),
        "captured_at_utc": row.get("captured_at_utc"),
        "kickoff_utc": row.get("kickoff_utc"),
        "minutes_to_kickoff": _num(row.get("minutes_to_kickoff")),
        "source_workflow_run": row.get("source_workflow_run"),
        "source_head_sha": row.get("source_head_sha"),
        "source_trigger_head_sha": row.get("source_trigger_head_sha"),
        "source_market_provider": row.get("source_market_provider"),
        "source_market_credential_mode": row.get("source_market_credential_mode"),
        "source_provenance_sha256": row.get("source_provenance_sha256"),
        "market_artifact_sha256": row.get("market_artifact_sha256"),
        "sportsbook_count": artifact.get("sportsbook_count"),
        "line_range": artifact.get("line_range"),
        "line_stddev": artifact.get("line_stddev"),
    }


def build_closing_event(
    source: Mapping[str, Any],
    archive_rows: Iterable[Mapping[str, Any]],
    *,
    as_of: datetime | None = None,
) -> dict[str, Any] | None:
    now = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    kickoff = source["kickoff"]
    if now < kickoff + ARCHIVE_SETTLEMENT_GRACE:
        return None

    rows = list(archive_rows)
    close = select_closing_row(source, rows)
    if close is None:
        return None
    original_basis = select_original_price_basis(source, rows)

    prop_type = str(source["prop_type"])
    kind = str(source.get("probability_kind") or "")
    side = _model_side(source)
    original_line = _num(source.get("original_line"))
    original_event_probability = _num(source.get("original_market_probability"))
    close_artifact = close["market_artifact"]
    closing_line = _num(close_artifact.get("consensus_line"))
    closing_event_probability = _event_probability(close_artifact, kind)

    raw_line_move = None
    side_line_clv = None
    if kind == "over" and original_line is not None and closing_line is not None:
        raw_line_move = closing_line - original_line
        if side == "over":
            side_line_clv = raw_line_move
        elif side == "under":
            side_line_clv = -raw_line_move

    binary = prop_type in BINARY_TD_MARKETS or kind == "td"
    original_price = None
    closing_price = None
    price_decimal_clv = None
    price_implied_probability_clv_pp = None
    if side is not None and original_basis is not None:
        original_price = _best_exact_threshold_price(
            original_basis["market_artifact"],
            side=side,
            threshold=original_line,
            binary=binary,
        )
        closing_price = _best_exact_threshold_price(
            close_artifact,
            side=side,
            threshold=original_line,
            binary=binary,
        )
        if original_price is not None and closing_price is not None:
            price_decimal_clv = (
                float(original_price["decimal"]) - float(closing_price["decimal"])
            )
            price_implied_probability_clv_pp = 100.0 * (
                float(closing_price["implied_probability"])
                - float(original_price["implied_probability"])
            )

    closing_side_probability = (
        _side_probability(close_artifact, side, kind) if side is not None else None
    )
    record = {
        "contract_version": CONTRACT_VERSION,
        "source_props21_forecast_sha256": source["source_sha"],
        "source_props21_forecast_id": source["source_id"],
        "game_id": source["game_id"],
        "player_id": source["player_id"],
        "prop_type": prop_type,
        "forecast_timestamp_utc": source["forecast"].isoformat(),
        "kickoff_utc": kickoff.isoformat(),
        "frozen_model_side": side,
        "original_market": {
            "line": original_line,
            "event_probability": original_event_probability,
            "archive_price_basis": (
                _archive_provenance(original_basis) if original_basis is not None else None
            ),
        },
        "closing_market": {
            "line": closing_line,
            "event_probability": closing_event_probability,
            "frozen_side_probability": closing_side_probability,
            "archive": _archive_provenance(close),
        },
        "line_clv": {
            "available": side_line_clv is not None,
            "raw_closing_minus_original_line": raw_line_move,
            "side_oriented_line_clv": side_line_clv,
        },
        "same_threshold_price_clv": {
            "available": (
                original_price is not None
                and closing_price is not None
                and price_decimal_clv is not None
                and price_implied_probability_clv_pp is not None
            ),
            "threshold": None if binary else original_line,
            "side": side,
            "original_best_price": original_price,
            "closing_best_price": closing_price,
            "decimal_odds_clv_original_minus_close": price_decimal_clv,
            "implied_probability_clv_pp_close_minus_original": (
                price_implied_probability_clv_pp
            ),
        },
        "selection": {
            "latest_valid_capture_strictly_before_kickoff": True,
            "capture_at_or_after_forecast": True,
            "archive_settlement_grace_minutes": int(
                ARCHIVE_SETTLEMENT_GRACE.total_seconds() // 60
            ),
            "outcome_consulted": False,
        },
        "research_only": True,
        "production_authorized": False,
    }
    record["closing_event_sha256"] = _sha(record)
    return record


def build_events(
    receipts: Iterable[Mapping[str, Any]],
    archive_rows: Iterable[Mapping[str, Any]],
    *,
    as_of: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    sources = collapse_source_forecasts(receipts)
    archive = [dict(row) for row in archive_rows]
    for row in archive:
        _validate_archive_row(row)
        _has_live_provenance(row)

    events: list[dict[str, Any]] = []
    pending_grace = 0
    unmatched = 0
    for source in sources:
        now = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if now < source["kickoff"] + ARCHIVE_SETTLEMENT_GRACE:
            pending_grace += 1
            continue
        event = build_closing_event(source, archive, as_of=now)
        if event is None:
            unmatched += 1
            continue
        events.append(event)
    events.sort(
        key=lambda row: (
            str(row["game_id"]),
            str(row["player_id"]),
            str(row["prop_type"]),
            str(row["source_props21_forecast_sha256"]),
        )
    )
    return events, {
        "source_forecasts": len(sources),
        "matched_closing_events": len(events),
        "unmatched_after_settlement": unmatched,
        "pending_archive_settlement_grace": pending_grace,
    }


def append_immutable(path: Path, rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    existing = read_jsonl(path)
    by_source: dict[str, dict[str, Any]] = {}
    for row in existing:
        source_sha = str(row.get("source_props21_forecast_sha256") or "").strip()
        event_sha = str(row.get("closing_event_sha256") or "").strip()
        if not source_sha or not event_sha:
            raise ClosingMarketError("existing closing event missing immutable identity")
        prior = by_source.get(source_sha)
        if prior is not None and prior.get("closing_event_sha256") != event_sha:
            raise ClosingMarketError(f"conflicting existing closing event: {source_sha}")
        by_source[source_sha] = row

    appended: list[Mapping[str, Any]] = []
    replayed = 0
    for row in rows:
        source_sha = str(row.get("source_props21_forecast_sha256") or "").strip()
        event_sha = str(row.get("closing_event_sha256") or "").strip()
        if not source_sha or not event_sha:
            raise ClosingMarketError("new closing event missing immutable identity")
        prior = by_source.get(source_sha)
        if prior is not None:
            if prior.get("closing_event_sha256") != event_sha:
                raise ClosingMarketError(f"immutable closing event conflict: {source_sha}")
            replayed += 1
            continue
        by_source[source_sha] = dict(row)
        appended.append(row)

    if appended:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for row in appended:
                handle.write(_canonical(row) + "\n")
    return {"appended": len(appended), "replayed": replayed, "total": len(by_source)}


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--status", type=Path)
    parser.add_argument("--as-of")
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    receipts = read_jsonl(args.receipts)
    if not receipts:
        if not args.allow_empty:
            raise SystemExit("Props 2.2 receipts are empty")
        summary = {
            "contract_version": CONTRACT_VERSION,
            "source_forecasts": 0,
            "archive_rows": 0,
            "matched_closing_events": 0,
            "unmatched_after_settlement": 0,
            "pending_archive_settlement_grace": 0,
            "append": {"appended": 0, "replayed": 0, "total": len(read_jsonl(args.output))},
            "research_only": True,
            "production_authorized": False,
        }
    else:
        archive = load_archive_rows(args.archive_root)
        as_of = (
            _timestamp(args.as_of, label="as_of")
            if args.as_of
            else datetime.now(timezone.utc)
        )
        events, counts = build_events(receipts, archive, as_of=as_of)
        append = append_immutable(args.output, events)
        summary = {
            "contract_version": CONTRACT_VERSION,
            **counts,
            "archive_rows": len(archive),
            "append": append,
            "research_only": True,
            "production_authorized": False,
        }

    if args.status is not None:
        args.status.parent.mkdir(parents=True, exist_ok=True)
        args.status.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
