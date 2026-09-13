from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.v09b_modern_dnp_weekly_roster_diagnostic_v1 import run_diagnostic


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
    report = run_diagnostic(
        archive_root=Path(args.archive_root),
        output_root=Path(args.output_root),
        contract=contract,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
