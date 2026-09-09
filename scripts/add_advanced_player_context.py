from __future__ import annotations

import argparse
import json
from pathlib import Path

from nfl_forecast.advanced_player_context import build_ngs_qb_evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    out = Path(args.output_dir)
    evidence_path = out / "contextual_evidence.json"
    status_path = out / "context_source_status.json"
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    evidence, ngs_status = build_ngs_qb_evidence(evidence, args.season)
    status["nextgen_qb_context"] = ngs_status
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
