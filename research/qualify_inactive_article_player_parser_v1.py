from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from research.inactive_article_player_parser_v1 import (
    parse_inactive_article_html,
    qualify_against_contract,
    receipt_json,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--archive-gzip", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--rows", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    artifact = contract["calibration_artifact"]
    with gzip.open(args.archive_gzip, "rb") as handle:
        raw_html = handle.read()

    parsed = parse_inactive_article_html(
        raw_html,
        source_url=artifact["article_url"],
        captured_at_utc=artifact["first_capture_known_by_utc"],
        raw_html_sha256=artifact["raw_html_sha256"],
    )
    receipt = qualify_against_contract(parsed, contract)

    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(receipt_json(receipt), encoding="utf-8")
    args.rows.parent.mkdir(parents=True, exist_ok=True)
    with args.rows.open("w", encoding="utf-8") as handle:
        for row in parsed.rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(receipt_json(receipt), end="")
    if not receipt["qualification_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
