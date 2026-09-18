from __future__ import annotations

"""Run one fail-closed live LevLine Props Research Beta publication cycle.

This coordinator does not alter the Props model or F-ST. It composes the existing
frozen upstream, live-market, manifest, simulation, and publication contracts into
one atomic production handoff for Sunday Signal.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_publication import append_jsonl_immutable, read_jsonl  # noqa: E402

RESEARCH_LABEL = "LEVLINE PROPS — RESEARCH BETA"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_priors(path: Path) -> dict[str, Any]:
    priors = _load_json(path)
    routes = priors.get("route_prior_means")
    if not isinstance(routes, dict):
        raise ValueError("Props priors require route_prior_means")
    for position in ("RB", "WR", "TE"):
        if position not in routes:
            raise ValueError(f"Props route priors missing {position}")
        try:
            mean = float(routes[position])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Props route prior for {position} must be numeric") from exc
        if not 0.0 < mean < 1.0:
            raise ValueError(f"Props route prior for {position} must be within (0, 1)")

    availability = priors.get("availability_beta_priors")
    if not isinstance(availability, dict) or "UNKNOWN" not in availability:
        raise ValueError("Props priors require availability_beta_priors.UNKNOWN")
    unknown = availability["UNKNOWN"]
    if not isinstance(unknown, dict):
        raise ValueError("UNKNOWN availability prior must be an object")
    for key in ("alpha", "beta"):
        try:
            value = float(unknown[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"UNKNOWN availability prior requires positive {key}") from exc
        if value <= 0:
            raise ValueError(f"UNKNOWN availability prior {key} must be positive")
    return priors


def resolve_target_week(path: Path) -> tuple[int, int]:
    if not path.exists():
        raise FileNotFoundError(f"canonical weekly slate is missing: {path}")
    pairs: set[tuple[int, int]] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = str(row.get("season") or "").strip()
            week = str(row.get("week") or "").strip()
            if not season or not week:
                continue
            pairs.add((int(float(season)), int(float(week))))
    if len(pairs) != 1:
        raise ValueError(
            "canonical weekly slate must resolve to exactly one season/week; "
            f"found {sorted(pairs)}"
        )
    return next(iter(pairs))


def _run(*args: object) -> None:
    command = [str(value) for value in args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copyfile(source, tmp)
    os.replace(tmp, destination)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one governed live LevLine Props cycle.")
    parser.add_argument("--season", type=int)
    parser.add_argument("--week", type=int)
    parser.add_argument(
        "--weekly-slate",
        type=Path,
        default=ROOT / "outputs" / "this_week.csv",
        help="Canonical Sunday Signal slate used to resolve season/week when omitted.",
    )
    parser.add_argument("--priors", type=Path, required=True)
    parser.add_argument(
        "--validate-priors-only",
        action="store_true",
        help="Validate the frozen preregistered priors and exit without live network access.",
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=ROOT / ".artifacts" / "props-live",
        help="Ephemeral immutable run captures; not published to the repository.",
    )
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "props")
    parser.add_argument("--api-key-env", default="THE_ODDS_API_KEY")
    parser.add_argument("--regions", default="us")
    parser.add_argument("--bookmakers")
    args = parser.parse_args()

    if (args.season is None) != (args.week is None):
        raise ValueError("--season and --week must be supplied together")
    season, week = (
        (args.season, args.week)
        if args.season is not None
        else resolve_target_week(args.weekly_slate)
    )
    if season is None or week is None or season < 2026 or week < 1:
        raise ValueError("invalid target season/week")

    validate_priors(args.priors)
    if args.validate_priors_only:
        print(f"validated frozen LevLine Props priors -> {args.priors}")
        return 0
    if not str(os.environ.get(args.api_key_env, "")).strip():
        raise RuntimeError(
            f"live Props market capture requires configured {args.api_key_env}"
        )

    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%S%fZ")
    run_root = args.work_root / run_id
    if run_root.exists():
        raise FileExistsError(f"refusing to reuse live Props run directory: {run_root}")

    upstream = run_root / "upstream"
    market = run_root / "market.json"
    raw_market = run_root / "market.raw.json"
    manifests = run_root / "manifests"
    staged_forecasts = run_root / "forecasts.json"
    staged_public = run_root / "public_props.json"
    staged_ledger = run_root / "forecast_originals.jsonl"

    _run(
        sys.executable,
        ROOT / "scripts" / "build_props_upstream_snapshot.py",
        "--season", season,
        "--week", week,
        "--all-games",
        "--priors", args.priors,
        "--output-dir", upstream,
    )

    market_command: list[object] = [
        sys.executable,
        ROOT / "scripts" / "build_props_market_snapshot.py",
        "--player-state", upstream / "player_state.json",
        "--output", market,
        "--raw-output", raw_market,
        "--api-key-env", args.api_key_env,
        "--regions", args.regions,
    ]
    if args.bookmakers:
        market_command.extend(["--bookmakers", args.bookmakers])
    _run(*market_command)

    market_payload = _load_json(market)
    market_rows = market_payload.get("market_artifacts")
    if not isinstance(market_rows, list) or not market_rows:
        raise RuntimeError(
            "live Props capture returned no normalized market artifacts; "
            "refusing to replace the current published slate"
        )

    _run(
        sys.executable,
        ROOT / "scripts" / "build_props_integration_manifest.py",
        "--upstream-slate", upstream / "upstream_slate.json",
        "--market-snapshot", market,
        "--output-dir", manifests,
    )
    _run(
        sys.executable,
        ROOT / "scripts" / "run_props_research_beta.py",
        "--manifest-slate", manifests / "manifest_slate.json",
        "--output", staged_forecasts,
        "--public-output", staged_public,
        "--history-ledger", staged_ledger,
    )

    forecast_payload = _load_json(staged_forecasts)
    public_payload = _load_json(staged_public)
    forecasts = forecast_payload.get("forecasts")
    summary = public_payload.get("summary")
    if not isinstance(forecasts, list) or not forecasts:
        raise RuntimeError("live Props cycle produced no forecasts; refusing publication")
    if not isinstance(summary, dict) or int(summary.get("total") or 0) != len(forecasts):
        raise RuntimeError("live Props public summary does not reconcile to forecast rows")

    receipts = read_jsonl(staged_ledger)
    if len(receipts) != len(forecasts):
        raise RuntimeError("live Props immutable receipt count does not reconcile")
    permanent_ledger = args.output_root / "history" / "forecast_originals.jsonl"
    append_jsonl_immutable(permanent_ledger, receipts, identity_key="forecast_id")

    current_forecasts = args.output_root / "forecasts.json"
    current_public = args.output_root / "public_props.json"
    _atomic_copy(staged_forecasts, current_forecasts)
    _atomic_copy(staged_public, current_public)

    status = {
        "contract_version": "levline-props-live-status-v0.1",
        "research_label": RESEARCH_LABEL,
        "run_id": run_id,
        "season": int(season),
        "week": int(week),
        "started_utc": started.isoformat(),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_count": len(forecasts),
        "market_artifact_count": len(market_rows),
        "public_summary": summary,
        "current_forecasts": str(current_forecasts.relative_to(ROOT)),
        "current_public": str(current_public.relative_to(ROOT)),
        "immutable_forecast_ledger": str(permanent_ledger.relative_to(ROOT)),
        "winner_model_mutated": False,
    }
    _write_json(args.output_root / "status.json", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
