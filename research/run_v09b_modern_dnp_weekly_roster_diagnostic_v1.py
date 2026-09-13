from __future__ import annotations

import argparse
import json
from pathlib import Path

import research.v09b_modern_dnp_weekly_roster_diagnostic_v1 as diagnostic
from research.v09b_modern_dnp_bbox_parser_v2 import (
    PARSER_VERSION,
    parse_all_dnp_tokens_bbox,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-root", required=True)
    parser.add_argument(
        "--contract",
        default="research/availability/v09b_modern_dnp_weekly_roster_diagnostic_contract_v1.json",
    )
    parser.add_argument(
        "--output-root",
        default="research_outputs/v09b_modern_dnp_weekly_roster_diagnostic_v1",
    )
    args = parser.parse_args()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))

    # Post-first-run parser correction only. The V1 source/qualification contract remains
    # unchanged and still has zero qualification authority.
    diagnostic.parse_all_dnp_tokens = parse_all_dnp_tokens_bbox
    output_root = Path(args.output_root)
    report = diagnostic.run_diagnostic(
        archive_root=Path(args.archive_root),
        output_root=output_root,
        contract=contract,
    )
    report["dnp_parser_version"] = PARSER_VERSION
    report["parser_correction_post_first_run"] = True
    report["interpretation"]["parser_correction_has_qualification_authority"] = False
    (output_root / "diagnostic_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
