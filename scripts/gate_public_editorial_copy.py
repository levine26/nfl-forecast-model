from __future__ import annotations

"""Enforce HUMAN claim authority at the independent GitHub Pages build boundary.

Even a direct commit which forges editorial source-status booleans must not
show an unsupported HUMAN Read. The site copy is downgraded rather than
blocking numerically valid official LevLine forecasts.
"""

import argparse
import csv
import json
from pathlib import Path

from scripts.editorial_signed_acceptance import (
    ClaimAcceptanceBlocked, require_signed_claim_receipts,
)
from scripts.verify_human_source_acceptance import (
    SourceAcceptanceBlocked, require_verified_human_sources,
)


def gate_site_editorial_copy(
    *,
    status_path: Path,
    forecast: Path,
    previews: Path,
    dossier: Path,
) -> dict:
    status = json.loads(status_path.read_text(encoding="utf-8"))
    with forecast.open(encoding="utf-8-sig", newline="") as handle:
        count = len(list(csv.DictReader(handle)))
    reason = ""
    try:
        require_verified_human_sources(status, games_expected=count)
        require_signed_claim_receipts(forecast=forecast, previews=previews, dossier=dossier)
        allowed = True
    except (SourceAcceptanceBlocked, ClaimAcceptanceBlocked) as exc:
        allowed = False
        reason = type(exc).__name__
    result = dict(status)
    acceptance = dict(status.get("editorial_acceptance") or {})
    if not allowed:
        acceptance.update({
            "status": "degraded",
            "article_resolution_verified": False,
            "claim_support_verified": False,
        })
    result["editorial_acceptance"] = acceptance
    result["public_editorial_release_gate"] = {
        "status": "verified_independent_review" if allowed else "source_or_claim_review_required",
        "independently_verified_human_read_publication": allowed,
        "reason_code": reason,
        "games_checked": count,
        "policy": "Official numeric forecasts stay visible; HUMAN story requires both source gate and signed external factual review.",
    }
    status_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result["public_editorial_release_gate"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--status", type=Path, default=Path("site/public/data/context_source_status.json"))
    p.add_argument("--forecast", type=Path, default=Path("site/public/data/this_week.csv"))
    p.add_argument("--previews", type=Path, default=Path("site/public/data/game_previews.json"))
    p.add_argument("--dossier", type=Path, default=Path("inputs/sunday_signal/independent_claim_approvals.json"))
    args = p.parse_args()
    result = gate_site_editorial_copy(status_path=args.status, forecast=args.forecast,
                                      previews=args.previews, dossier=args.dossier)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
