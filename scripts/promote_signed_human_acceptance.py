from __future__ import annotations

"""Only independently verified, signed HUMAN claim receipts may promote release status.

The deterministic finalizer correctly records structural eligibility without
pretending that source content or factual claims have been verified. This
restricted adapter makes external signed authority usable without letting a
provider JSON flag, URL shape or two-paragraph validator promote a Read.
"""

import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from scripts.editorial_signed_acceptance import (
    ClaimAcceptanceBlocked, require_signed_claim_receipts,
)


def promote_verified_acceptance(
    status_path: Path = Path("outputs/context_source_status.json"),
    forecast: Path = Path("outputs/this_week.csv"),
    previews: Path = Path("outputs/game_previews.json"),
    dossier: Path = Path("inputs/sunday_signal/independent_claim_approvals.json"),
) -> dict:
    status = json.loads(status_path.read_text(encoding="utf-8"))
    with forecast.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = len(rows)
    audit = status.get("editorial_acceptance")
    if not isinstance(audit, dict) or expected < 1:
        raise ClaimAcceptanceBlocked("missing current canonical structural editorial audit")
    if (audit.get("games_expected") != expected
            or audit.get("games_with_structurally_eligible_human_reads") != expected
            or audit.get("games_rejected") != 0
            or audit.get("issues")
            or audit.get("status") not in {"structurally_eligible", "healthy"}):
        raise ClaimAcceptanceBlocked("structural HUMAN Read acceptance is incomplete; signing cannot bypass rejected prose")
    # First independently validate the FULL signed dossier, covering every
    # canonical game/paragraph, including all public citations.
    proof = require_signed_claim_receipts(forecast=forecast, previews=previews, dossier=dossier)
    if proof.get("games_verified_by_signed_independent_review") != expected:
        raise ClaimAcceptanceBlocked("signed independent review did not cover all canonical games")
    result = dict(status)
    accepted = dict(audit)
    accepted.update({
        "status": "healthy",
        "article_resolution_verified": True,
        "claim_support_verified": True,
        "independent_signed_claim_review": {
            "mechanism": "Ed25519 independent reviewer attestation",
            "dossier_sha256": sha256(dossier.read_bytes()).hexdigest(),
            "canonical_slate_sha256": proof["canonical_slate_sha256"],
            "games_verified": expected,
        },
    })
    result["editorial_acceptance"] = accepted
    # Write only AFTER all trusted validations; replace atomically so an
    # interrupted reviewer handoff does not erase the last-good status.
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=status_path.parent,
                                     prefix=".editorial-audit-", delete=False) as output:
        temp_name = output.name
        output.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temp_name, status_path)
    return {"status": "healthy", "games_verified": expected,
            "dossier_sha256": accepted["independent_signed_claim_review"]["dossier_sha256"]}


def main() -> None:
    result = promote_verified_acceptance()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
