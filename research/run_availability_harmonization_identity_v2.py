from __future__ import annotations

"""Deterministic v2 identity bridge for the 2022-2025 availability audit.

PR #145's frozen reverse-identity gate failed on 2022 because official NFL pages use
common/nickname forms that differ from the nflverse injury row's full/legal name. This
module does not relax that gate. It adds a separately preregistered, identity-only bridge:
exact aliases from a pinned nflverse player master may resolve an otherwise unresolved
official row only when exactly one alias-matched GSIS ID is present in the same
season/week/team nflverse injury rows.

No fuzzy matching, manual alias list, cross-week imputation, model fitting, game outcome,
actual snap, or completed-2026 information is permitted.
"""

import argparse
import hashlib
import json
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from nfl_forecast.availability_2025_reconstruction import (
    attach_stable_identity,
    normalize_name_token,
)
from research import run_availability_harmonization_repaired_v1 as repaired


IDENTITY_CONTRACT_PATH = Path("research/availability/2022_2025_identity_bridge_contract_v2.json")
PLAYER_MASTER_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
PLAYER_MASTER_EXPECTED_SHA256 = "6f896e1134757efe09761ae81280f89d9604d8ce611a888a56d9e7d49e80eeb9"
PLAYER_MASTER_REQUIRED_FIELDS = {
    "gsis_id",
    "display_name",
    "football_name",
    "common_first_name",
    "first_name",
    "last_name",
}
PLAYER_MASTER_ALIAS_FIELDS = (
    "display_name",
    "football_name",
)

_PLAYER_MASTER: pd.DataFrame | None = None
_ALIAS_LOOKUP: dict[str, tuple[str, ...]] = {}
_BRIDGE_RESOLVED: dict[int, pd.DataFrame] = {}
_ORIGINAL_RECORD_REVERSE_IDENTITY = repaired._record_reverse_identity


def _load_contract() -> dict:
    return json.loads(IDENTITY_CONTRACT_PATH.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_player_master_payload(payload: bytes) -> pd.DataFrame:
    digest = _sha256(payload)
    if digest != PLAYER_MASTER_EXPECTED_SHA256:
        raise ValueError(
            "nflverse player-master digest changed: "
            f"expected {PLAYER_MASTER_EXPECTED_SHA256}, got {digest}"
        )
    frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
    missing = PLAYER_MASTER_REQUIRED_FIELDS - set(frame.columns)
    if missing:
        raise ValueError(f"nflverse player master missing fields: {sorted(missing)}")
    ids = frame["gsis_id"].fillna("").astype(str).str.strip()
    if ids.eq("").any():
        raise ValueError("nflverse player master contains missing GSIS IDs")
    if ids.duplicated().any():
        raise ValueError("nflverse player master contains duplicate GSIS primary keys")
    return frame


def _name_aliases(row: pd.Series) -> set[str]:
    raw: list[object] = [row.get(field, "") for field in PLAYER_MASTER_ALIAS_FIELDS]
    raw.extend([
        f"{row.get('first_name', '')} {row.get('last_name', '')}",
        f"{row.get('common_first_name', '')} {row.get('last_name', '')}",
    ])
    aliases = {normalize_name_token(value) for value in raw}
    aliases.discard("")
    aliases.discard("nan")
    aliases.discard("none")
    return aliases


def build_player_master_alias_lookup(frame: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    missing = PLAYER_MASTER_REQUIRED_FIELDS - set(frame.columns)
    if missing:
        raise ValueError(f"nflverse player master missing fields: {sorted(missing)}")
    lookup: dict[str, set[str]] = {}
    for _, row in frame.iterrows():
        gsis_id = str(row.get("gsis_id", "")).strip()
        if not gsis_id or gsis_id.lower() in {"nan", "none"}:
            continue
        for alias in _name_aliases(row):
            lookup.setdefault(alias, set()).add(gsis_id)
    return {alias: tuple(sorted(ids)) for alias, ids in lookup.items()}


def _injury_presence_lookup(nflverse: pd.DataFrame, *, season: int) -> dict[tuple[int, int, str], set[str]]:
    base = repaired._identity_base(nflverse, season=season)
    lookup: dict[tuple[int, int, str], set[str]] = {}
    for row in base.itertuples(index=False):
        key = (int(row.season), int(row.week), str(row.team))
        lookup.setdefault(key, set()).add(str(row.gsis_id))
    return lookup


def attach_stable_identity_v2(
    official: pd.DataFrame,
    nflverse: pd.DataFrame,
    player_master: pd.DataFrame,
    *,
    season: int,
) -> pd.DataFrame:
    """Resolve identity with exact injury names first, then exact player-master aliases.

    Alias resolution is valid only when exactly one alias-matched GSIS ID is also present
    in the same season/week/team injury rows. This keeps the bridge identity-only and
    prevents a current master name from manufacturing a historical roster/injury state.
    """
    base = repaired._identity_base(nflverse, season=season)
    matched = attach_stable_identity(official, base)
    alias_lookup = build_player_master_alias_lookup(player_master)
    presence = _injury_presence_lookup(base, season=season)

    for idx in matched.index[~matched["identity_match_state"].eq("unique")]:
        row = matched.loc[idx]
        alias = normalize_name_token(row.get("external_player", ""))
        alias_ids = set(alias_lookup.get(alias, ()))
        same_week_ids = presence.get((int(row["season"]), int(row["week"]), str(row["team"])), set())
        candidates = tuple(sorted(alias_ids & same_week_ids))
        if len(candidates) == 1:
            matched.at[idx, "gsis_id"] = candidates[0]
            matched.at[idx, "identity_match_state"] = "unique"
            matched.at[idx, "identity_match_method"] = "player_master_exact_alias_plus_injury_presence"
        elif len(candidates) > 1:
            matched.at[idx, "gsis_id"] = ""
            matched.at[idx, "identity_match_state"] = "ambiguous"
            matched.at[idx, "identity_match_method"] = "player_master_alias_ambiguous_after_injury_presence"
        else:
            prior = str(row.get("identity_match_method", ""))
            matched.at[idx, "identity_match_method"] = (
                f"{prior}+player_master_no_unique_same_week_candidate" if prior else
                "player_master_no_unique_same_week_candidate"
            )
    return matched


def reverse_identity_audit_v2(
    official: pd.DataFrame,
    nflverse: pd.DataFrame,
    player_master: pd.DataFrame,
    *,
    season: int,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    matched = attach_stable_identity_v2(official, nflverse, player_master, season=season)
    unique = matched["identity_match_state"].eq("unique")
    bridge = matched["identity_match_method"].eq("player_master_exact_alias_plus_injury_presence")
    total = int(len(matched))
    resolved = int(unique.sum())
    unresolved = matched.loc[~unique].copy()
    bridged = matched.loc[bridge].copy()
    rate = float(resolved / total) if total else 0.0
    metrics = {
        "season": int(season),
        "official_distinct_rows": total,
        "official_unique_stable_identity_rows": resolved,
        "official_unresolved_identity_rows": int(len(unresolved)),
        "official_identity_resolution_rate": rate,
        "identity_bridge_resolved_rows": int(len(bridged)),
        "identity_bridge_unique_official_names": int(bridged["external_player"].nunique()) if len(bridged) else 0,
        "identity_bridge_method": "exact_player_master_alias_plus_same_team_week_injury_presence",
        "identity_bridge_fuzzy_matching_used": False,
        "identity_bridge_manual_alias_overrides_used": False,
    }
    return metrics, unresolved, bridged


def _record_reverse_identity_v2(
    official: pd.DataFrame,
    nflverse: pd.DataFrame,
    *,
    season: int,
) -> None:
    # Preserve 2025's already-passing reverse-identity evidence exactly. The v2 bridge
    # exists to repair the legacy-season identity naming gap exposed by the v1 audit.
    if int(season) == 2025:
        return _ORIGINAL_RECORD_REVERSE_IDENTITY(official, nflverse, season=season)
    if _PLAYER_MASTER is None:
        raise RuntimeError("player master must be loaded before legacy reverse-identity audit")

    contract = repaired._load_contract()
    threshold = float(contract["qualification_gates"]["official_identity_resolution_rate_min"])
    metrics, unresolved, bridged = reverse_identity_audit_v2(
        official, nflverse, _PLAYER_MASTER, season=season
    )
    metrics["official_identity_resolution_rate_min"] = threshold
    metrics["official_identity_gate_passed"] = metrics["official_identity_resolution_rate"] >= threshold
    repaired._AUDIT.setdefault(int(season), {}).update(metrics)
    _BRIDGE_RESOLVED[int(season)] = bridged
    if repaired._OUTPUT_DIR is not None:
        unresolved.to_csv(repaired._OUTPUT_DIR / f"official_identity_unresolved_{season}.csv", index=False)
        bridged.to_csv(repaired._OUTPUT_DIR / f"official_identity_bridge_resolved_{season}.csv", index=False)
        _write_json(repaired._OUTPUT_DIR / "official_reverse_identity_audit.json", repaired._AUDIT)
    if not metrics["official_identity_gate_passed"]:
        raise ValueError(
            f"{season} official->nflverse stable identity resolution "
            f"{metrics['official_identity_resolution_rate']:.6f} is below frozen gate {threshold:.6f}"
        )


def _load_player_master(output_dir: Path) -> dict:
    global _PLAYER_MASTER, _ALIAS_LOOKUP
    contract = _load_contract()
    source = contract["source"]
    if source["expected_sha256"] != PLAYER_MASTER_EXPECTED_SHA256:
        raise RuntimeError("identity contract/player-master digest constant drift")
    if float(contract["qualification_policy"]["official_identity_resolution_rate_min"]) != 0.995:
        raise RuntimeError("v2 identity contract changed frozen reverse-identity threshold")
    if contract["identity_rule"]["fuzzy_matching_allowed"] is not False:
        raise RuntimeError("v2 identity contract must prohibit fuzzy matching")
    if contract["identity_rule"]["manual_alias_overrides_allowed"] is not False:
        raise RuntimeError("v2 identity contract must prohibit manual alias overrides")

    session = requests.Session()
    payload = repaired.base_runner._fetch(session, PLAYER_MASTER_URL)
    digest = _sha256(payload)
    raw_path = output_dir / "raw" / "nflverse" / "players.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)
    _PLAYER_MASTER = validate_player_master_payload(payload)
    _ALIAS_LOOKUP = build_player_master_alias_lookup(_PLAYER_MASTER)
    source_record = {
        "source": "nflverse_player_master",
        "url": PLAYER_MASTER_URL,
        "release_asset_id": source["release_asset_id"],
        "bytes": len(payload),
        "sha256": digest,
        "rows": int(len(_PLAYER_MASTER)),
        "alias_keys": int(len(_ALIAS_LOOKUP)),
        "required_fields": sorted(PLAYER_MASTER_REQUIRED_FIELDS),
        "allowed_alias_fields": source["allowed_alias_fields"],
    }
    _write_json(output_dir / "player_master_identity_source.json", source_record)
    return source_record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/availability_2022_2025_harmonization")
    parser.add_argument("--reconstruction-2025-dir", default="research_outputs/availability_2025_reconstruction")
    parser.add_argument("--require-qualified", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    reconstruction_2025_dir = Path(args.reconstruction_2025_dir)

    repaired._OUTPUT_DIR = output_dir
    repaired._AUDIT.clear()
    _BRIDGE_RESOLVED.clear()
    source_record = _load_player_master(output_dir)

    # Reuse the v1 exact-duplicate and source-state implementation unchanged, replacing
    # only the reverse identity accounting function for legacy seasons.
    repaired.base_runner._collect_official_season = repaired._collect_official_with_exact_dedupe
    repaired.base_runner.build_season_reconstruction = repaired._build_season_with_reverse_accounting
    original_record = _ORIGINAL_RECORD_REVERSE_IDENTITY
    repaired._record_reverse_identity = _record_reverse_identity_v2

    result: dict | None = None
    try:
        repaired._audit_qualified_2025(reconstruction_2025_dir)
        result = repaired.base_runner.collect(output_dir, reconstruction_2025_dir=reconstruction_2025_dir)
        result["official_reverse_identity_audit"] = {
            str(k): v for k, v in sorted(repaired._AUDIT.items())
        }
        result["identity_bridge_v2"] = {
            "contract": str(IDENTITY_CONTRACT_PATH),
            "player_master_source": source_record,
            "threshold_relaxation": False,
            "fuzzy_matching_used": False,
            "manual_alias_overrides_used": False,
            "game_outcomes_consulted": False,
            "completed_2026_outcomes_consulted": False,
            "production_authorized": False,
            "probability_feature_authorized": False,
        }
        _write_json(output_dir / "qualification_with_identity_bridge_v2.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
        if args.require_qualified and not bool(result.get("qualified")):
            return 1
        return 0
    finally:
        repaired._record_reverse_identity = original_record
        _write_json(
            output_dir / "official_reverse_identity_audit.json",
            {str(k): v for k, v in sorted(repaired._AUDIT.items())},
        )


if __name__ == "__main__":
    raise SystemExit(main())
