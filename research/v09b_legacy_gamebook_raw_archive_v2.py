from __future__ import annotations

"""V2 source-structure audit for official 2012-2016 NFLGSIS Game Books.

V1 is preserved as a failed parser-specification experiment. V2 changes only heading
recognition: official pdftotext -layout output may render the Not Active and Did Not Play
headings without colons. All source, coverage, integrity and governance gates remain V1's
fail-closed gates.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from research import v09b_legacy_gamebook_raw_archive_v1 as v1

ARCHIVE_ID = "V09B-LEGACY-GAMEBOOK-BYTES-2012-2016-V2"
PARSER_VERSION = "V09B-GAMEBOOK-TEXT-STRUCTURE-V2"
CONTRACT_ID = "V09B-LEGACY-GAMEBOOK-RAW-ARCHIVE-V2"
NOT_ACTIVE_LINE_RE = re.compile(r"(?im)^[ \t]*Not[ \t]+Active\b")
DID_NOT_PLAY_LINE_RE = re.compile(r"(?im)^[ \t]*Did[ \t]+Not[ \t]+Play\b")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_structure_signals_v2(text: str) -> dict[str, Any]:
    not_active = list(NOT_ACTIVE_LINE_RE.finditer(text))
    did_not_play = list(DID_NOT_PLAY_LINE_RE.finditer(text))
    not_active_valid = len(not_active) >= 1
    did_not_play_valid = len(did_not_play) >= 1
    return {
        "not_active_heading_occurrences": len(not_active),
        "did_not_play_heading_occurrences": len(did_not_play),
        "not_active_structure_valid": not_active_valid,
        "did_not_play_structure_valid": did_not_play_valid,
        "semantic_headings_distinct": bool(not_active_valid and did_not_play_valid),
        "text_sha256": _sha256_text(text),
        "text_length": len(text),
    }


def archive_season_v2(
    season: int,
    *,
    archive_root: Path,
    timeout: float = 30.0,
    attempts: int = 3,
) -> dict[str, Any]:
    old_archive_id = v1.ARCHIVE_ID
    old_parser_version = v1.PARSER_VERSION
    old_signals = v1.source_structure_signals
    v1.ARCHIVE_ID = ARCHIVE_ID
    v1.PARSER_VERSION = PARSER_VERSION
    v1.source_structure_signals = source_structure_signals_v2
    try:
        receipt = v1.archive_season(
            season,
            archive_root=archive_root,
            timeout=timeout,
            attempts=attempts,
        )
    finally:
        v1.ARCHIVE_ID = old_archive_id
        v1.PARSER_VERSION = old_parser_version
        v1.source_structure_signals = old_signals

    receipt["contract_id"] = CONTRACT_ID
    receipt["archive_id"] = ARCHIVE_ID
    receipt["parser_version"] = PARSER_VERSION
    receipt["v1_failure_preserved"] = True
    receipt["coverage_thresholds_relaxed_from_v1"] = False
    receipt["label_semantics_changed_from_v1"] = False
    return receipt


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(v1.EXPECTED_GAMES))
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(list(argv) if argv is not None else None)

    receipt = archive_season_v2(
        args.season,
        archive_root=args.archive_root,
        timeout=args.timeout,
        attempts=args.attempts,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: value for k, value in receipt.items() if k != "error_rows"}, indent=2, sort_keys=True))
    if receipt["all_frozen_gates_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
