from __future__ import annotations

"""Frozen numerical and serialization core for ATS Frontier V3 Key-Mass.

Research/shadow only. This module has no production forecast imports and exposes no
outcome-scoring entry point. It represents the entire integer lattice analytically:
a market-centered constant-scale Student-t distribution is integrated over exact
integer bins and only 0, +/-3, +/-7 receive finite log-mass adjustments.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import t as student_t

CANDIDATE_ID = "FV3-PROS-KMASS-01"
NULL_ID = "FV3-NULL-STUDENTT-CONSTANT-01"
HORIZON = "T-120m"
KEY_MARGINS = (0, -3, 3, -7, 7)
EPS = 1e-15
FORBIDDEN_OUTCOME_KEYS = frozenset({
    "home_score", "away_score", "actual_margin", "final_margin", "result",
    "winner", "ats_result", "ats_class", "cover_result", "game_result",
})

class V3ContractError(RuntimeError):
    pass

def _utc(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise V3ContractError(f"invalid timestamp: {value}") from exc
    if dt.tzinfo is None:
        raise V3ContractError("timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)

def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")

def sha256_hex(value: bytes) -> str:
    return sha256(value).hexdigest()

def assert_no_outcome_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_OUTCOME_KEYS:
                raise V3ContractError(f"outcome field prohibited before confirmatory scoring: {key}")
            assert_no_outcome_fields(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            assert_no_outcome_fields(item)

def canonical_home_margin_from_bookmaker_home_point(home_point: float) -> float:
    """Convert standard sportsbook home handicap point to expected home margin."""
    x = float(home_point)
    if not math.isfinite(x):
        raise V3ContractError("home spread must be finite")
    return -x

def base_cell(m: int, loc: float, sigma: float, nu: float) -> float:
    s = float(sigma)
    if not math.isfinite(s) or s <= 0:
        raise V3ContractError("sigma must be finite and positive")
    df = float(nu)
    if not math.isfinite(df) or df <= 2:
        raise V3ContractError("Student-t degrees of freedom must exceed 2")
    hi = student_t.cdf((float(m) + 0.5 - float(loc)) / s, df=df)
    lo = student_t.cdf((float(m) - 0.5 - float(loc)) / s, df=df)
    return float(max(0.0, hi - lo))

def _weight(m: int, gammas: Sequence[float]) -> float:
    if len(gammas) != 3:
        raise V3ContractError("gammas must be [gamma0, gamma3, gamma7]")
    g0, g3, g7 = (float(x) for x in gammas)
    if not all(math.isfinite(x) for x in (g0, g3, g7)):
        raise V3ContractError("gammas must be finite")
    if int(m) == 0:
        return math.exp(g0)
    if abs(int(m)) == 3:
        return math.exp(g3)
    if abs(int(m)) == 7:
        return math.exp(g7)
    return 1.0

def normalizer(loc: float, sigma: float, nu: float, gammas: Sequence[float]) -> float:
    z = 1.0
    for m in KEY_MARGINS:
        p0 = base_cell(m, loc, sigma, nu)
        z += (_weight(m, gammas) - 1.0) * p0
    if not math.isfinite(z) or z <= 0:
        raise V3ContractError("invalid analytic PMF normalizer")
    return float(z)

def cell(m: int, loc: float, sigma: float, nu: float, gammas: Sequence[float]) -> float:
    return float(base_cell(int(m), loc, sigma, nu) * _weight(int(m), gammas) / normalizer(loc, sigma, nu, gammas))

def _base_leq(k: int, loc: float, sigma: float, nu: float) -> float:
    return float(student_t.cdf((float(k) + 0.5 - float(loc)) / float(sigma), df=float(nu)))

def leq(k: int, loc: float, sigma: float, nu: float, gammas: Sequence[float]) -> float:
    correction = 0.0
    for m in KEY_MARGINS:
        if m <= int(k):
            correction += (_weight(m, gammas) - 1.0) * base_cell(m, loc, sigma, nu)
    p = (_base_leq(int(k), loc, sigma, nu) + correction) / normalizer(loc, sigma, nu, gammas)
    if not math.isfinite(p) or p < -1e-12 or p > 1 + 1e-12:
        raise V3ContractError("invalid cumulative PMF")
    return float(min(1.0, max(0.0, p)))

def _integer_line(line: float) -> bool:
    return math.isclose(float(line), round(float(line)), abs_tol=1e-10)

def cpl_probs(loc: float, sigma: float, nu: float, gammas: Sequence[float], market_margin_line: float) -> tuple[float, float, float]:
    line = float(market_margin_line)
    if _integer_line(line):
        m = int(round(line))
        loss = leq(m - 1, loc, sigma, nu, gammas)
        push = cell(m, loc, sigma, nu, gammas)
        cover = 1.0 - loss - push
    else:
        k = math.floor(line)
        loss = leq(k, loc, sigma, nu, gammas)
        push = 0.0
        cover = 1.0 - loss
    vals = np.asarray([cover, push, loss], dtype=float)
    if not np.isfinite(vals).all() or (vals < -1e-12).any():
        raise V3ContractError("invalid CPL probabilities")
    vals = np.clip(vals, 0.0, 1.0)
    vals /= vals.sum()
    return tuple(float(x) for x in vals)

def pmf_descriptor(loc: float, sigma: float, nu: float, gammas: Sequence[float]) -> dict[str, Any]:
    return {
        "representation": "analytic_unbounded_integer_pmf",
        "family": "market_centered_student_t_exact_integer_bins",
        "location": float(loc), "scale": float(sigma), "degrees_of_freedom": float(nu),
        "key_log_mass_offsets": {"0": float(gammas[0]), "abs3": float(gammas[1]), "abs7": float(gammas[2])},
        "normalizer": normalizer(loc, sigma, nu, gammas),
        "finite_support": False, "endpoint_folding": False,
    }

REQUIRED_RECORD_FIELDS = (
    "schema_version", "candidate_id", "null_id", "game_id", "season", "week",
    "kickoff_timestamp_utc", "prediction_timestamp_utc", "market_provider",
    "market_horizon", "market_target_timestamp_utc", "market_request_timestamp_utc",
    "market_quote_max_timestamp_utc", "market_event_id", "market_source_count",
    "market_source_names", "raw_home_spread_point", "canonical_home_margin",
    "home_spread_price", "away_spread_price", "candidate_pmf", "null_pmf",
    "candidate_cover_push_loss", "null_cover_push_loss", "raw_input_hash",
    "model_code_hash", "config_hash",
)

def validate_prediction_record(record: Mapping[str, Any]) -> None:
    assert_no_outcome_fields(record)
    missing = [k for k in REQUIRED_RECORD_FIELDS if k not in record]
    if missing:
        raise V3ContractError(f"missing prediction fields: {missing}")
    if record["candidate_id"] != CANDIDATE_ID or record["null_id"] != NULL_ID:
        raise V3ContractError("candidate/null identity mismatch")
    if record["market_horizon"] != HORIZON:
        raise V3ContractError("market horizon mismatch")
    kickoff = _utc(str(record["kickoff_timestamp_utc"]))
    prediction = _utc(str(record["prediction_timestamp_utc"]))
    target = _utc(str(record["market_target_timestamp_utc"]))
    request = _utc(str(record["market_request_timestamp_utc"]))
    quote = _utc(str(record["market_quote_max_timestamp_utc"]))
    if prediction >= kickoff:
        raise V3ContractError("prediction must be serialized before kickoff")
    if request > target or quote > target:
        raise V3ContractError("market timestamp is after frozen T-120 cutoff")
    if target >= kickoff:
        raise V3ContractError("market target must precede kickoff")
    if int(record["market_source_count"]) < 2:
        raise V3ContractError("fewer than two sportsbooks cannot form governed consensus")
    for key in ("candidate_cover_push_loss", "null_cover_push_loss"):
        probs = record[key]
        if set(probs) != {"cover", "push", "loss"}:
            raise V3ContractError(f"{key} must contain cover/push/loss")
        vals = [float(probs[x]) for x in ("cover", "push", "loss")]
        if any((not math.isfinite(v) or v < 0 or v > 1) for v in vals) or not math.isclose(sum(vals), 1.0, abs_tol=1e-12):
            raise V3ContractError(f"{key} invalid")
    for key in ("raw_input_hash", "model_code_hash", "config_hash"):
        value = str(record[key])
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise V3ContractError(f"{key} must be lowercase sha256 hex")

def finalize_prediction_record(record: Mapping[str, Any]) -> dict[str, Any]:
    base = dict(record)
    base.pop("prediction_hash", None)
    validate_prediction_record(base)
    base["prediction_hash"] = sha256_hex(canonical_json_bytes(base))
    return base

def serialize_prediction_record(record: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(finalize_prediction_record(record))

def append_immutable_jsonl(path: str | Path, record: Mapping[str, Any]) -> str:
    finalized = finalize_prediction_record(record)
    identity = (finalized["candidate_id"], finalized["game_id"], finalized["market_horizon"])
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        with p.open("rb") as handle:
            for raw in handle:
                if not raw.strip():
                    continue
                prior = json.loads(raw)
                if (prior.get("candidate_id"), prior.get("game_id"), prior.get("market_horizon")) == identity:
                    raise V3ContractError(f"immutable prediction already exists: {identity}")
    payload = canonical_json_bytes(finalized)
    with p.open("ab") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    return str(finalized["prediction_hash"])
