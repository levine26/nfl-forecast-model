from __future__ import annotations

"""Capture and freeze sportsbook inputs for LevLine Props Research Beta.

Live mode requires an authorized sportsbook credential supplied through an environment
variable. Offline mode accepts an already captured provider payload for deterministic QA.
Credentials are never written to disk.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_market_live import (  # noqa: E402
    build_market_snapshot,
    fetch_live_nfl_prop_events,
    fetch_live_nfl_prop_events_with_fallback,
    payload_sha256,
)


def _load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _player_state_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("player_state") or payload.get("rows")
    else:
        rows = None
    if not isinstance(rows, list) or not rows:
        raise ValueError("player-state input must contain a non-empty JSON row list")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("player-state rows must be JSON objects")
    return [dict(row) for row in rows]


def _provider_events(payload) -> list[dict]:
    if isinstance(payload, dict) and "event_odds" in payload:
        payload = payload["event_odds"]
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("provider payload must be an event object or list of event objects")
    if not all(isinstance(row, dict) for row in payload):
        raise ValueError("provider event payloads must be JSON objects")
    return [dict(row) for row in payload]


def _aware(value: str, label: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _write_frozen(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture/freeze LevLine Props sportsbook market artifacts."
    )
    parser.add_argument("--player-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--raw-output",
        type=Path,
        help="Immutable raw provider capture path; defaults next to --output.",
    )
    parser.add_argument(
        "--provider-payload",
        type=Path,
        help="Offline captured The Odds API-style event payload. If omitted, fetch live.",
    )
    parser.add_argument(
        "--captured-at",
        help="Required in offline mode. In live mode the truthful post-fetch UTC time is used.",
    )
    parser.add_argument(
        "--provider",
        choices=("auto", "the_odds_api", "propline", "sportsgameodds"),
        default="auto",
        help=(
            "Live sportsbook provider. auto tries The Odds API, PropLine, "
            "then SportsGameOdds."
        ),
    )
    parser.add_argument("--api-key-env", default="THE_ODDS_API_KEY")
    parser.add_argument("--propline-api-key-env", default="PROPLINE_API_KEY")
    parser.add_argument(
        "--sportsgameodds-api-key-env",
        default="SPORTSGAMEODDS_API_KEY",
    )
    parser.add_argument("--regions", default="us")
    parser.add_argument(
        "--bookmakers",
        help="Optional comma-separated bookmaker keys/IDs for the selected provider.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()

    raw_output = args.raw_output or args.output.with_name(
        f"{args.output.stem}.raw{args.output.suffix or '.json'}"
    )
    for path in (args.output, raw_output):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite frozen capture: {path}")

    player_state_rows = _player_state_rows(_load_json(args.player_state))

    if args.provider_payload is not None:
        if not args.captured_at:
            raise ValueError("--captured-at is required with --provider-payload")
        captured = _aware(args.captured_at, "--captured-at")
        raw_payload = _load_json(args.provider_payload)
        provider_events = _provider_events(raw_payload)
        selected_provider = "the_odds_api" if args.provider == "auto" else args.provider
        raw_bundle = {
            "provider": selected_provider,
            "capture_mode": "offline_payload",
            "captured_at_utc": captured.isoformat(),
            "event_odds": provider_events,
        }
    else:
        the_odds_api_key = os.environ.get(args.api_key_env, "")
        propline_api_key = os.environ.get(args.propline_api_key_env, "")
        sportsgameodds_api_key = os.environ.get(
            args.sportsgameodds_api_key_env,
            "",
        )
        if args.provider == "auto":
            provider_events, raw_bundle = fetch_live_nfl_prop_events_with_fallback(
                player_state_rows=player_state_rows,
                the_odds_api_key=the_odds_api_key,
                propline_api_key=propline_api_key,
                sportsgameodds_api_key=sportsgameodds_api_key,
                regions=args.regions,
                bookmakers=args.bookmakers,
                timeout_seconds=args.timeout_seconds,
            )
        else:
            key_by_provider = {
                "the_odds_api": the_odds_api_key,
                "propline": propline_api_key,
                "sportsgameodds": sportsgameodds_api_key,
            }
            env_by_provider = {
                "the_odds_api": args.api_key_env,
                "propline": args.propline_api_key_env,
                "sportsgameodds": args.sportsgameodds_api_key_env,
            }
            key = key_by_provider[args.provider]
            key_env = env_by_provider[args.provider]
            if not key.strip():
                raise RuntimeError(
                    f"live capture requires an authorized {args.provider} credential in {key_env}"
                )
            provider_events, raw_bundle = fetch_live_nfl_prop_events(
                player_state_rows=player_state_rows,
                api_key=key,
                regions=args.regions,
                bookmakers=args.bookmakers,
                timeout_seconds=args.timeout_seconds,
                provider=args.provider,
            )
        selected_provider = str(raw_bundle.get("provider") or "")
        captured = datetime.now(timezone.utc)
        raw_bundle = {
            **raw_bundle,
            "capture_mode": "live_api",
            "captured_at_utc": captured.isoformat(),
        }

    snapshot = build_market_snapshot(
        player_state_rows=player_state_rows,
        provider_events=provider_events,
        captured_at_utc=captured,
        provider=selected_provider,
    )
    raw_bundle = {
        **raw_bundle,
        "payload_sha256": payload_sha256(provider_events),
        "normalized_snapshot_sha256": payload_sha256(snapshot),
    }

    # Check both destinations before either immutable write so a pre-existing path cannot
    # create a half-published pair.
    for path in (args.output, raw_output):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite frozen capture: {path}")
    _write_frozen(raw_output, raw_bundle)
    _write_frozen(args.output, snapshot)

    print(
        f"frozen {len(snapshot['market_artifacts'])} market artifacts "
        f"from {snapshot['audit']['matched_event_count']} events -> {args.output}"
    )
    print(f"raw provider capture -> {raw_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
