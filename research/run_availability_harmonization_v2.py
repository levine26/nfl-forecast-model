from __future__ import annotations

"""Run the preregistered v2 2022-2025 availability harmonization audit.

V2 changes identity resolution only. The football state, official-page cross-check,
T-120 chronology, missingness, and quantitative qualification gates remain the same as
v1. No model fitting or outcome scoring occurs here.
"""

import argparse
import json
from pathlib import Path

import requests

import research.availability_harmonization_v1 as harmonization_core
from research import run_availability_harmonization_repaired_v1 as repaired
from research.availability_identity_v2 import (
    PLAYER_MASTER_ASSET_ID,
    PLAYER_MASTER_EXPECTED_SHA256,
    PLAYER_MASTER_URL,
    attach_stable_identity_v2,
    build_player_alias_lookup,
    sha256_bytes,
    validate_player_master_payload,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--output-dir", default="research_outputs/availability_2022_2025_harmonization")
    parser.add_argument("--reconstruction-2025-dir", default="research_outputs/availability_2025_reconstruction")
    parser.add_argument("--require-qualified", action="store_true")
    args, _ = parser.parse_known_args()

    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw" / "identity"
    raw_dir.mkdir(parents=True, exist_ok=True)

    response = requests.get(PLAYER_MASTER_URL, timeout=90)
    response.raise_for_status()
    payload = response.content
    digest = sha256_bytes(payload)
    (raw_dir / "players.csv").write_bytes(payload)
    player_master = validate_player_master_payload(payload)
    alias_lookup = build_player_alias_lookup(player_master)

    source_receipt = {
        "source": "nflverse players",
        "release_asset_id": PLAYER_MASTER_ASSET_ID,
        "url": PLAYER_MASTER_URL,
        "sha256": digest,
        "expected_sha256": PLAYER_MASTER_EXPECTED_SHA256,
        "sha256_matches": digest == PLAYER_MASTER_EXPECTED_SHA256,
        "gsis_keyed_rows": int(len(player_master)),
        "normalized_alias_keys": int(len(alias_lookup)),
        "identity_only": True,
        "latest_team_used": False,
        "status_used": False,
        "position_used_to_choose_identity": False,
        "game_or_practice_status_used_to_choose_identity": False,
        "completed_2026_outcomes_used": False,
    }
    _write_json(output_dir / "player_master_source_receipt.json", source_receipt)

    def bound_attach(external, nflverse):
        return attach_stable_identity_v2(external, nflverse, player_master)

    # The historical builder imported v1 identity as a module global, and the repair
    # wrapper imported it separately for reverse coverage. Patch both explicitly so
    # canonical->official and official->canonical accounting use the same v2 identity
    # contract. No state/chronology function is replaced.
    harmonization_core.attach_stable_identity = bound_attach
    repaired.attach_stable_identity = bound_attach

    try:
        return int(repaired.main())
    finally:
        _write_json(output_dir / "player_master_source_receipt.json", source_receipt)


if __name__ == "__main__":
    raise SystemExit(main())
