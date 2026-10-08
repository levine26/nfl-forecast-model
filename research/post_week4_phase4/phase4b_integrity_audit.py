"""Read-only 2026 scheduled-game denominator and local two-stage integrity audit.

IMPORTANT: This cannot certify an external timestamp, source completeness,
true WORM storage or a statistically eligible prospective prediction.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

from research.post_week4_phase4.c_shadow import canonical_hash, iso_utc
from research.post_week4_phase4.two_stage_gateway import (
    FROZEN_MODEL_CANONICAL_SHA256, STAGE_SCHEMA, GATEWAY_SCHEMA,
)


def _load(path: Path):
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def audit_local_denominator(store: Path, scheduled_games: list[dict]) -> dict:
    """Correlate explicit schedule denominator, stages, seals and failures.

    May identify local corruption and missingness, but *always* reports
    0 certified prospective records absent a separate trusted witness audit.
    """
    root = Path(store)
    if not isinstance(scheduled_games, list) or not scheduled_games:
        raise ValueError("Complete independently witnessed schedule needed")
    universe = {}
    for game in scheduled_games:
        gid = game.get("game_id")
        if not gid or gid in universe:
            raise ValueError("Duplicate/missing scheduled game ID")
        ko = iso_utc(game.get("kickoff_utc"), "scheduled kickoff")
        if not isinstance(game.get("week"), int) or not isinstance(game.get("season"), int):
            raise ValueError("Malformed schedule")
        universe[gid] = {**game, "kickoff": ko}
    rows = []
    errors = []
    for gid, target in universe.items():
        stage_file = root / "staged" / f"{gid}.json"
        prediction_file = root / "predictions" / f"{gid}.json"
        record = {"game_id":gid, "season":target["season"],"week":target["week"],
                  "stage_present": stage_file.is_file(),
                  "prediction_present":prediction_file.is_file(),
                  "locally_consistent":False, "prospective_qualified":False}
        try:
            if prediction_file.is_file() and not stage_file.is_file():
                raise ValueError("Prediction exists without earlier stage")
            if stage_file.is_file():
                s,sd = _load(stage_file)
                raw = s.get("football_input",{})
                if (s.get("schema") != STAGE_SCHEMA or s.get("game_id") != gid or
                    s.get("football_input_sha256") != canonical_hash(raw)):
                    raise ValueError("Corrupt staged input or digest")
                if raw.get("kickoff_utc") != target["kickoff_utc"] or raw.get("week") != target["week"] or raw.get("season") != target["season"]:
                    raise ValueError("Schedule rescheduled/identity drift")
                captured = iso_utc(s.get("captured_at_utc"), "raw capture")
                if captured >= target["kickoff"]:
                    raise ValueError("Football stage after kickoff")
                if prediction_file.is_file():
                    p,pd = _load(prediction_file)
                    if (p.get("gateway_schema") != GATEWAY_SCHEMA or
                        p.get("game_id") != gid or
                        p.get("raw_stage_file_sha256") != sd or
                        p.get("frozen_model_sha256") != FROZEN_MODEL_CANONICAL_SHA256 or
                        p.get("candidate_id") != "EARLY-STATE-SHRINKAGE-V1-SHADOW-2026-10-07" or
                        p.get("gateway_pit_checks_passed") is not True):
                        raise ValueError("Prediction payload or stage/model seal mismatch")
                    sealed = iso_utc(p.get("shadow_sealed_at_utc"), "shadow seal")
                    if sealed < captured or sealed >= target["kickoff"]:
                        raise ValueError("Sealed before capture or after kickoff")
                record["locally_consistent"] = True
            else:
                record["reason"] = "NO_PREGAME_STAGE"
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            record["reason"] = str(exc)
            errors.append({"game_id":gid,"error":str(exc)})
        rows.append(record)
    # Unknown objects must not silently enter an analyzed sample.
    stage_files = {p.stem for p in (root/"staged").glob("*.json")}
    pred_files = {p.stem for p in (root/"predictions").glob("*.json")}
    unexpected = sorted((stage_files|pred_files)-set(universe))
    if unexpected:
        errors.append({"error":"Objects outside trusted schedule denominator",
                       "game_ids":unexpected})
    failure_dir = root / "failures"
    failure_count = len(list(failure_dir.glob("*.json"))) if failure_dir.exists() else 0
    return {
       "audit_schema":"phase4b_local_denominator_audit_v1",
       "scheduled_games":len(universe),
       "scheduled_distinct_weeks":len({(v["season"],v["week"]) for v in universe.values()}),
       "stage_count":sum(r["stage_present"] for r in rows),
       "sealed_count":sum(r["prediction_present"] for r in rows),
       "failure_ledger_count":failure_count,
       "errors":errors, "unexpected_ids":unexpected, "per_game":rows,
       "external_source_clock_verified":False,
       "external_lock_publication_verified":False,
       "durable_worm_receipt_verified":False,
       "independently_qualified_prospective_predictions":0,
       "independently_qualified_non_tie_games":0,
       "live_activation_authorized":False,
    }
