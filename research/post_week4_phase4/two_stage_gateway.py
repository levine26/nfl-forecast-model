"""Two-stage research-only Candidate C shadow gateway.

No live adapters are bundled. The only way to produce a qualified record is to
supply independently implemented source and official-lock verification callbacks.
Never use this code as a justification for treating caller-supplied old timestamps
or a current prediction-history CSV as prospective proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Callable

from research.post_week4_phase4.c_shadow import (
    CANDIDATE_ID, CONTRACT_ID, PRODUCTION_ID, canonical_hash, hexsha,
    iso_utc, number, score_snapshot, validate_model,
)

STAGE_SCHEMA = "c_shadow_raw_stage_v1"
GATEWAY_SCHEMA = "c_shadow_two_stage_gateway_v1"
# SHA-256 over canonical JSON of the immutable checked-in frozen C artifact.
FROZEN_MODEL_CANONICAL_SHA256 = "6af9358922321c3a03f9285df384e96cbe2d59f6d9780d2cd1ddf7d39c1ccdd5"
_SHA40 = re.compile(r"[0-9a-f]{40}")


def _now(clock=None) -> datetime:
    value = clock() if clock else datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Independent capture clock must provide aware datetime")
    return value.astimezone(timezone.utc)


def _stamp(dt: datetime) -> str:
    return dt.isoformat()


def _dump(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _game_id(raw: dict) -> str:
    if not isinstance(raw, dict):
        raise ValueError("Source envelope must be object")
    season, week = raw.get("season"), raw.get("week")
    away, home = raw.get("away_team"), raw.get("home_team")
    if (type(season) is not int or season < 2026 or type(week) is not int or not 1 <= week <= 18
        or not isinstance(home, str) or not isinstance(away, str)
        or not re.fullmatch(r"[A-Z]{2,3}", home) or not re.fullmatch(r"[A-Z]{2,3}", away)
        or home == away or raw.get("game_id") != f"{season}_{week:02d}_{away}_{home}"):
        raise ValueError("Incorrect game, season, week or canonical team identity")
    return raw["game_id"]


def _create_once(path: Path, payload: dict) -> tuple[str, bool]:
    """Exclusive creation: retry with same exact bytes is idempotent, not a rewrite."""
    data = _dump(payload)
    if path.is_file():
        existing = path.read_bytes()
        if existing != data:
            raise FileExistsError("Conflicting sealed object: replacement forbidden")
        return _digest(existing), False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.read_bytes() != data:
            raise FileExistsError("Concurrent conflicting sealed object") from None
        return _digest(data), False
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    return _digest(data), True


def _failure(root: Path, operation: str, game: str, error: Exception) -> None:
    """Never erase a rejected attempt; local OS filesystem is not a WORM service."""
    moment = datetime.now(timezone.utc).isoformat()
    record = {"operation": operation, "game_id": str(game), "observed_utc": moment,
              "error_type": type(error).__name__, "reason": str(error),
              "prospective_eligible": False}
    # Unique event allows repeated failures to be retained. No raw licensed data.
    folder = root / "failures"
    folder.mkdir(parents=True, exist_ok=True)
    for counter in range(50):
        basename = f"{moment.replace(':', '-')}_{os.getpid()}_{counter}.json"
        try:
            _create_once(folder / basename, record)
            return
        except FileExistsError:
            continue
    raise RuntimeError("Cannot preserve failure ledger") from error


def capture_raw(raw: dict, root: Path, *, source_verifier: Callable | None = None,
                clock: Callable | None = None) -> dict:
    """Stage football inputs BEFORE official lock. No market, outcome or F-ST data."""
    root = Path(root)
    game = raw.get("game_id", "unknown") if isinstance(raw, dict) else "unknown"
    try:
        game = _game_id(raw)
        forbidden = ("outcome", "home_score", "away_score", "fst_home_prob", "market_home_prob",
                     "fst_lock_timestamp_utc", "fst_lock_status", "snapshot_captured_utc",
                     "candidate_home_prob", "final_home_prob", "lock_status")
        if any(k in raw for k in forbidden):
            raise ValueError("Raw football stage contains locked forecast or outcome")
        if raw.get("contract") != CONTRACT_ID or raw.get("team_state_builder_id") != "EARLY-STATE-SHRINKAGE-V1":
            raise ValueError("Unknown frozen C input contract")
        now = _now(clock)
        kickoff = iso_utc(raw.get("kickoff_utc"), "kickoff")
        observed = iso_utc(raw.get("features_observed_at_utc"), "source observed")
        source_asof = iso_utc(raw.get("feature_source_asof_utc"), "source asof")
        if not source_asof <= observed <= now < kickoff:
            raise ValueError("Late/future-dated source or already-started game")
        if (now - source_asof).total_seconds() > 7200:
            raise ValueError("Stale source at football capture")
        hexsha(raw.get("raw_source_sha256"), "raw source hash")
        hexsha(raw.get("schedule_source_sha256"), "schedule hash")
        if raw.get("upstream_completion_audit_passed") is not True:
            raise ValueError("Unqualified completed-game source")
        if not isinstance(raw.get("team_states"), dict) or set(raw["team_states"]) != {"home", "away"}:
            raise ValueError("Both team histories required")
        # Check every reported prior-game observation before the actual capture.
        for side, team in (("home", raw["home_team"]), ("away", raw["away_team"])):
            state = raw["team_states"][side]
            if not isinstance(state, dict) or state.get("team") != team:
                raise ValueError("Wrong team state")
            for name in ("last_eight_previous_season", "current_season_completed"):
                games = state.get(name)
                if not isinstance(games, list):
                    raise ValueError("Missing previous-game manifest")
                for previous in games:
                    if iso_utc(previous.get("stats_observed_utc"), "prior stats observed") > now:
                        raise ValueError("Future prior-game source observation")
        proof = source_verifier(raw) if source_verifier is not None else None
        if proof is not None and (not isinstance(proof, dict) or
                                  proof.get("complete_asof_capture") is not True or
                                  proof.get("storage_rights_verified") is not True or
                                  not isinstance(proof.get("verification_ref"), str) or
                                  not proof["verification_ref"] or
                                  proof.get("football_input_sha256") != canonical_hash(raw)):
            raise ValueError("Independent source verifier did not qualify coverage/rights")
        payload = {"schema": STAGE_SCHEMA, "game_id": game, "captured_at_utc": _stamp(now),
                   "football_input_sha256": canonical_hash(raw), "football_input": raw,
                   "source_proof": proof, "prospective_qualified": False}
        path = root / "staged" / f"{game}.json"
        if path.is_file():
            previous = json.loads(path.read_text())
            if previous.get("football_input_sha256") != payload["football_input_sha256"]:
                raise FileExistsError("Conflicting game capture; cannot overwrite")
            # Source/capture time is never revised by an idempotent retry.
            return {"stage_sha256": _digest(path.read_bytes()), "stage": previous,
                    "created": False, "path": str(path)}
        digest, created = _create_once(path, payload)
        return {"stage_sha256": digest, "stage": payload, "created": created, "path": str(path)}
    except Exception as error:
        _failure(root, "capture", game, error)
        raise


def seal_against_lock(root: Path, game_id: str, official: dict, model: dict, *,
                      lock_verifier: Callable | None = None, clock: Callable | None = None) -> dict:
    """Score only after a genuinely verified lock is published but before kickoff.

    lock_verifier must resolve *first publication* of this exact original LOCKED
    row externally, returning commit_sha/first_published_utc/row_sha256. No
    verifier is shipped; self-attestation is never sufficient for live enrollment.
    """
    root = Path(root)
    try:
        if lock_verifier is None:
            raise ValueError("Independent original-lock publication verifier missing")
        validate_model(model)
        if canonical_hash(model) != FROZEN_MODEL_CANONICAL_SHA256:
            raise ValueError("Frozen Candidate C artifact hash changed")
        path = root / "staged" / f"{game_id}.json"
        if not path.is_file():
            raise ValueError("No immutable earlier football capture")
        stage_data = path.read_bytes()
        stage = json.loads(stage_data)
        if stage.get("schema") != STAGE_SCHEMA or stage.get("game_id") != game_id:
            raise ValueError("Stage identity mismatch")
        raw = stage["football_input"]
        if _game_id(raw) != game_id or stage.get("football_input_sha256") != canonical_hash(raw):
            raise ValueError("Corrupt raw football hash/identity")
        proof = stage.get("source_proof")
        if (not isinstance(proof, dict) or proof.get("complete_asof_capture") is not True or
            proof.get("storage_rights_verified") is not True or
            proof.get("football_input_sha256") != canonical_hash(raw)):
            raise ValueError("Original football source/rights unverified")
        now = _now(clock)
        ko = iso_utc(raw["kickoff_utc"], "kickoff")
        capture_time = iso_utc(stage.get("captured_at_utc"), "first stage capture")
        if not capture_time <= now < ko:
            raise ValueError("Retroactive candidate scoring forbidden")
        if official.get("game_id") != game_id or any(
            official.get(k) != raw.get(k) for k in ("season", "week", "home_team", "away_team", "kickoff_utc")
        ):
            raise ValueError("Official lock game/teams/week/kickoff mismatch")
        if (official.get("lock_status") != "LOCKED" or
            official.get("fst_artifact_id") != PRODUCTION_ID or
            official.get("final_probability_strategy") != PRODUCTION_ID):
            raise ValueError("Official locked F-ST identity/status required")
        lock = iso_utc(official.get("lock_timestamp_utc"), "official lock")
        generated = iso_utc(official.get("prediction_timestamp_utc"), "official generated")
        market_time = iso_utc(official.get("market_snapshot_timestamp_utc"), "market observed")
        if not generated <= lock or not market_time <= lock:
            raise ValueError("Official prediction/market from after lock")
        if official.get("market_freshness_status") not in ("refreshed_this_run", "fresh"):
            raise ValueError("Original market freshness unqualified")
        number(official.get("final_home_prob"), "official probability", prob=True)
        number(official.get("market_home_prob"), "official market", prob=True)
        lock_proof = lock_verifier(official)
        if not isinstance(lock_proof, dict):
            raise ValueError("No independent first-publication proof")
        if (not isinstance(lock_proof.get("commit_sha"), str) or
            not _SHA40.fullmatch(lock_proof["commit_sha"]) or
            lock_proof.get("row_sha256") != canonical_hash(official)):
            raise ValueError("Official source SHA / row mismatch")
        publication = iso_utc(lock_proof.get("first_published_utc"), "first published")
        if not capture_time <= lock <= publication <= now < ko:
            raise ValueError("First publication after kickoff, before stage, or in future")
        snapshot = dict(raw)
        snapshot.update({
            "snapshot_captured_utc": _stamp(capture_time),
            "fst_lock_timestamp_utc": official["lock_timestamp_utc"],
            "fst_lock_status": "LOCKED", "fst_candidate_id": PRODUCTION_ID,
            "fst_home_prob": float(official["final_home_prob"]),
            "market_home_prob": float(official["market_home_prob"]),
        })
        candidate = score_snapshot(snapshot, model)
        candidate.update({
            "gateway_schema": GATEWAY_SCHEMA,
            "raw_stage_file_sha256": _digest(stage_data),
            "official_lock_row_sha256": canonical_hash(official),
            "official_lock_commit_sha": lock_proof["commit_sha"],
            "official_lock_first_published_utc": _stamp(publication),
            "shadow_sealed_at_utc": _stamp(now),
            "source_qualification_ref": proof["verification_ref"],
            "gateway_pit_checks_passed": True,
        })
        predicted = root / "predictions" / f"{game_id}.json"
        if predicted.is_file():
            existing = json.loads(predicted.read_text())
            if (existing.get("input_snapshot_sha256") != candidate["input_snapshot_sha256"] or
                existing.get("official_lock_row_sha256") != candidate["official_lock_row_sha256"] or
                existing.get("frozen_model_sha256") != candidate["frozen_model_sha256"]):
                raise FileExistsError("Sealed forecast conflict; cannot revise")
            return {"record": existing, "prediction_sha256": _digest(predicted.read_bytes()),
                    "created": False, "path": str(predicted)}
        digest, created = _create_once(predicted, candidate)
        return {"record": candidate, "prediction_sha256": digest, "created": created,
                "path": str(predicted)}
    except Exception as error:
        _failure(root, "seal", game_id, error)
        raise
