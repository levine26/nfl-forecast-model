from __future__ import annotations

"""Record immutable prospective LevLine Props 2.0 shadow probabilities.

The shadow is a post-processing research layer over already-frozen V1 forecasts.
It never changes the V1 artifact, public Props output, or LevLine/F-ST winner model.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_publication import append_jsonl_immutable, read_jsonl  # noqa: E402

EPS = 1e-4
EVENT_TYPE = "CHALLENGER_FORECAST_ORIGINAL"


class ShadowError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _dt(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _finite(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _probability(value: Any, *, open_interval: bool = False) -> float | None:
    parsed = _finite(value)
    if parsed is None:
        return None
    if open_interval:
        return parsed if 0.0 < parsed < 1.0 else None
    return parsed if 0.0 <= parsed <= 1.0 else None


def _clip_probability(value: float) -> float:
    return min(1.0 - EPS, max(EPS, float(value)))


def _logit(value: float) -> float:
    p = _clip_probability(value)
    return math.log(p / (1.0 - p))


def _inv_logit(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _direction(probability: float, *, tolerance: float = 1e-12) -> str | None:
    if probability > 0.5 + tolerance:
        return "OVER"
    if probability < 0.5 - tolerance:
        return "UNDER"
    return None


def _v1_direction(row: Mapping[str, Any]) -> str | None:
    market = row.get("market") if isinstance(row.get("market"), Mapping) else {}
    model = row.get("model") if isinstance(row.get("model"), Mapping) else {}
    line = _finite(market.get("line"))
    fair = _finite(model.get("fair_line"))
    if line is None or fair is None:
        return None
    if fair > line:
        return "OVER"
    if fair < line:
        return "UNDER"
    return None


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ShadowError("shadow config must be a JSON object")
    if config.get("contract_version") != "levline-props-v2-prospective-shadow-v0.1.0":
        raise ShadowError("unsupported prospective shadow contract")
    if config.get("production_authorized") is not False:
        raise ShadowError("prospective shadow must remain production unauthorized")
    if config.get("completed_2026_outcomes_used_for_selection_or_fit") is not False:
        raise ShadowError("shadow config may not use completed 2026 outcomes")
    supported = config.get("supported_prop_types")
    if not isinstance(supported, list) or not supported:
        raise ShadowError("shadow config requires supported_prop_types")
    residual = config.get("market_v1_residual")
    if not isinstance(residual, dict):
        raise ShadowError("shadow config requires market_v1_residual")
    for field in ("intercept", "residual_beta", "residual_l2", "intercept_l2"):
        if _finite(residual.get(field)) is None:
            raise ShadowError(f"shadow residual config missing finite {field}")
    return config


def _shadow_id(source_forecast_id: str, config: Mapping[str, Any]) -> str:
    residual = config["market_v1_residual"]
    identity = {
        "source_forecast_id": source_forecast_id,
        "shadow_contract_version": config["contract_version"],
        "market_only_version": config["market_only"]["version"],
        "market_v1_residual_version": residual["version"],
    }
    return "props_shadow_" + _sha(identity)[:24]


def build_shadow_receipt(
    row: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    recorded_utc: datetime,
    source_workflow_run: str,
    source_head_sha: str,
    source_trigger_head_sha: str,
    source_market_provider: str,
    source_market_credential_mode: str,
    source_provenance_sha256: str,
) -> dict[str, Any] | None:
    if recorded_utc.tzinfo is None:
        raise ShadowError("recorded_utc must be timezone-aware")
    recorded = recorded_utc.astimezone(timezone.utc)

    source_id = str(row.get("forecast_id") or "").strip()
    prop_type = str(row.get("prop_type") or "").strip()
    source_run = str(source_workflow_run or "").strip()
    source_sha = str(source_head_sha or "").strip().lower()
    trigger_sha = str(source_trigger_head_sha or "").strip().lower()
    market_provider = str(source_market_provider or "").strip()
    credential_mode = str(source_market_credential_mode or "").strip()
    provenance_sha = str(source_provenance_sha256 or "").strip().lower()
    if not source_run:
        raise ShadowError("source_workflow_run is required")
    if len(source_sha) not in {40, 64} or any(c not in "0123456789abcdef" for c in source_sha):
        raise ShadowError("source_head_sha must be a git SHA")
    if len(trigger_sha) not in {40, 64} or any(c not in "0123456789abcdef" for c in trigger_sha):
        raise ShadowError("source_trigger_head_sha must be a git SHA")
    if not market_provider:
        raise ShadowError("source_market_provider is required")
    if not credential_mode:
        raise ShadowError("source_market_credential_mode is required")
    if len(provenance_sha) != 64 or any(c not in "0123456789abcdef" for c in provenance_sha):
        raise ShadowError("source_provenance_sha256 must be SHA-256")
    if not source_id or prop_type not in set(config["supported_prop_types"]):
        return None

    kickoff = _dt(row.get("kickoff_utc"))
    forecast_at = _dt(row.get("forecast_timestamp_utc"))
    market = row.get("market") if isinstance(row.get("market"), Mapping) else {}
    model = row.get("model") if isinstance(row.get("model"), Mapping) else {}
    market_at = _dt(market.get("captured_utc"))
    if kickoff is None or forecast_at is None or market_at is None:
        return None
    if forecast_at >= kickoff or market_at >= kickoff or recorded >= kickoff:
        return None
    if forecast_at > recorded or market_at > recorded:
        return None

    market_p = _probability(market.get("no_vig_over_probability"), open_interval=True)
    v1_p = _probability(model.get("over_probability"))
    line = _finite(market.get("line"))
    if market_p is None or v1_p is None or line is None:
        return None

    residual = config["market_v1_residual"]
    intercept = float(residual["intercept"])
    beta = float(residual["residual_beta"])
    residual_p = _inv_logit(
        _logit(market_p)
        + intercept
        + beta * (_logit(v1_p) - _logit(market_p))
    )

    source_copy = json.loads(_canon(dict(row)))
    shadow_id = _shadow_id(source_id, config)
    receipt = {
        "shadow_history_contract_version": config["contract_version"],
        "event_type": EVENT_TYPE,
        "shadow_id": shadow_id,
        "recorded_utc": recorded.isoformat(),
        "source_workflow_run": source_run,
        "source_head_sha": source_sha,
        "source_trigger_head_sha": trigger_sha,
        "source_market_provider": market_provider,
        "source_market_credential_mode": credential_mode,
        "source_provenance_sha256": provenance_sha,
        "source_forecast_id": source_id,
        "source_forecast_sha256": _sha(source_copy),
        "source_forecast_timestamp_utc": forecast_at.isoformat(),
        "source_market_captured_utc": market_at.isoformat(),
        "kickoff_utc": kickoff.isoformat(),
        "game_id": str(row.get("game_id") or ""),
        "player_id": str(row.get("player_id") or ""),
        "player": str(row.get("player") or ""),
        "position": str(row.get("position") or ""),
        "team": str(row.get("team") or ""),
        "opponent": str(row.get("opponent") or ""),
        "prop_type": prop_type,
        "market_line": line,
        "market_no_vig_over_probability": market_p,
        "v1_over_probability": v1_p,
        "v1_fair_line": _finite(model.get("fair_line")),
        "v1_direction": _v1_direction(row),
        "market_only": {
            "version": config["market_only"]["version"],
            "p_over": market_p,
            "p_under": 1.0 - market_p,
            "direction": _direction(market_p),
        },
        "market_v1_residual": {
            "version": residual["version"],
            "p_over": residual_p,
            "p_under": 1.0 - residual_p,
            "direction": _direction(residual_p),
            "intercept": intercept,
            "residual_beta": beta,
        },
        "fit_provenance": config["fit_provenance"],
        "governance": {
            "production_authorized": False,
            "published_v1_props_mutated": False,
            "winner_model_mutated": False,
            "completed_2026_outcomes_used_for_selection_or_fit": False,
        },
    }
    receipt["shadow_sha256"] = _sha(receipt)
    return receipt


def record_shadow_receipts(
    artifact: Mapping[str, Any],
    config: Mapping[str, Any],
    ledger: Path,
    *,
    source_workflow_run: str,
    source_head_sha: str,
    source_trigger_head_sha: str,
    source_market_provider: str,
    source_market_credential_mode: str,
    source_provenance_sha256: str,
    recorded_utc: datetime | None = None,
) -> dict[str, Any]:
    rows = artifact.get("forecasts")
    if not isinstance(rows, list):
        raise ShadowError("forecast artifact must contain a forecasts list")
    recorded = recorded_utc or datetime.now(timezone.utc)
    if recorded.tzinfo is None:
        raise ShadowError("recorded_utc must be timezone-aware")

    existing = read_jsonl(ledger) if ledger.exists() else []
    existing_ids = {
        str(item.get("shadow_id"))
        for item in existing
        if isinstance(item, dict) and item.get("shadow_id")
    }

    receipts: list[dict[str, Any]] = []
    skipped_existing = 0
    ineligible = 0
    for row in rows:
        if not isinstance(row, Mapping):
            ineligible += 1
            continue
        source_id = str(row.get("forecast_id") or "").strip()
        candidate_id = _shadow_id(source_id, config) if source_id else None
        if candidate_id and candidate_id in existing_ids:
            skipped_existing += 1
            continue
        receipt = build_shadow_receipt(
            row,
            config,
            recorded_utc=recorded,
            source_workflow_run=source_workflow_run,
            source_head_sha=source_head_sha,
            source_trigger_head_sha=source_trigger_head_sha,
            source_market_provider=source_market_provider,
            source_market_credential_mode=source_market_credential_mode,
            source_provenance_sha256=source_provenance_sha256,
        )
        if receipt is None:
            ineligible += 1
            continue
        receipts.append(receipt)

    ledger.parent.mkdir(parents=True, exist_ok=True)
    appended = append_jsonl_immutable(ledger, receipts, identity_key="shadow_id") if receipts else 0
    return {
        "contract_version": config["contract_version"],
        "recorded_utc": recorded.astimezone(timezone.utc).isoformat(),
        "source_workflow_run": str(source_workflow_run),
        "source_head_sha": str(source_head_sha).lower(),
        "source_trigger_head_sha": str(source_trigger_head_sha).lower(),
        "source_market_provider": str(source_market_provider),
        "source_market_credential_mode": str(source_market_credential_mode),
        "source_provenance_sha256": str(source_provenance_sha256).lower(),
        "forecast_rows_received": len(rows),
        "eligible_new_shadow_receipts": len(receipts),
        "appended": int(appended),
        "skipped_existing": int(skipped_existing),
        "ineligible": int(ineligible),
        "ledger": str(ledger),
        "production_authorized": False,
        "winner_model_mutated": False,
        "published_v1_props_mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record prospective Props 2.0 shadow forecasts.")
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--source-workflow-run", required=True)
    parser.add_argument("--source-head-sha", required=True)
    parser.add_argument("--source-trigger-head-sha", required=True)
    parser.add_argument("--source-market-provider", required=True)
    parser.add_argument("--source-market-credential-mode", required=True)
    parser.add_argument("--source-provenance-sha256", required=True)
    args = parser.parse_args()

    artifact = json.loads(args.forecasts.read_text(encoding="utf-8"))
    if not isinstance(artifact, dict):
        raise ShadowError("forecast artifact must be a JSON object")
    config = load_config(args.config)
    result = record_shadow_receipts(
        artifact,
        config,
        args.ledger,
        source_workflow_run=args.source_workflow_run,
        source_head_sha=args.source_head_sha,
        source_trigger_head_sha=args.source_trigger_head_sha,
        source_market_provider=args.source_market_provider,
        source_market_credential_mode=args.source_market_credential_mode,
        source_provenance_sha256=args.source_provenance_sha256,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
