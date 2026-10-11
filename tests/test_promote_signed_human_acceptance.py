from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.editorial_signed_acceptance import ClaimAcceptanceBlocked
import scripts.promote_signed_human_acceptance as promotion


def inputs(tmp_path):
    forecast = tmp_path / "this_week.csv"
    with forecast.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["game_id", "pick"])
        writer.writeheader()
        writer.writerow({"game_id": "2026_05_TB_DAL", "pick": "DAL"})
    source = {
        "editorial_acceptance": {
            "status": "structurally_eligible",
            "games_expected": 1,
            "games_with_structurally_eligible_human_reads": 1,
            "games_rejected": 0,
            "issues": {},
            "article_resolution_verified": False,
            "claim_support_verified": False,
        },
        "official_model": "F-ST-01-FROZEN-2026",
    }
    status = tmp_path / "status.json"
    status.write_text(json.dumps(source))
    previews = tmp_path / "previews.json"
    previews.write_text("{}")
    dossier = tmp_path / "signed.json"
    dossier.write_text("{}")
    return status, forecast, previews, dossier


def test_signed_proof_promotes_structural_not_model_status(tmp_path, monkeypatch):
    paths = inputs(tmp_path)
    status, forecast, _, dossier = paths
    from hashlib import sha256
    monkeypatch.setattr(promotion, "require_signed_claim_receipts", lambda **kwargs: {
        "games_verified_by_signed_independent_review": 1,
        "canonical_slate_sha256": sha256(forecast.read_bytes()).hexdigest(),
    })
    result = promotion.promote_verified_acceptance(*paths)
    upgraded = json.loads(status.read_text())
    assert result["games_verified"] == 1
    assert upgraded["editorial_acceptance"]["claim_support_verified"] is True
    assert upgraded["editorial_acceptance"]["article_resolution_verified"] is True
    assert upgraded["editorial_acceptance"]["status"] == "healthy"
    assert upgraded["official_model"] == "F-ST-01-FROZEN-2026"
    assert result["dossier_sha256"] == sha256(dossier.read_bytes()).hexdigest()


def test_unsigned_or_unavailable_review_does_not_modify_previous_status(tmp_path, monkeypatch):
    paths = inputs(tmp_path)
    status = paths[0]
    raw = status.read_bytes()
    def reject(**kwargs):
        raise ClaimAcceptanceBlocked("independent signer not configured")
    monkeypatch.setattr(promotion, "require_signed_claim_receipts", reject)
    with pytest.raises(ClaimAcceptanceBlocked):
        promotion.promote_verified_acceptance(*paths)
    assert status.read_bytes() == raw


def test_signatures_cannot_override_structurally_rejected_games(tmp_path, monkeypatch):
    paths = inputs(tmp_path)
    status = paths[0]
    d = json.loads(status.read_text())
    d["editorial_acceptance"]["games_rejected"] = 1
    d["editorial_acceptance"]["games_with_structurally_eligible_human_reads"] = 0
    status.write_text(json.dumps(d))
    raw = status.read_bytes()
    monkeypatch.setattr(promotion, "require_signed_claim_receipts",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not review")))
    with pytest.raises(ClaimAcceptanceBlocked, match="structural"):
        promotion.promote_verified_acceptance(*paths)
    assert status.read_bytes() == raw


def test_publisher_workflows_only_promote_after_structural_finalizer():
    root = Path(__file__).resolve().parents[1]
    for p in ("chatgpt_failed_game_ingest.yml", "chatgpt_media_ingest.yml", "groq_media_writer.yml"):
        text = (root / ".github/workflows" / p).read_text()
        assert "promote_verified_acceptance()" in text
        assert text.rindex("promote_verified_acceptance()") < text.rindex(
            "require_verified_human_sources(status, games_expected=games)"
        )
        assert "SUNDAY_SIGNAL_REVIEW_PUBLIC_KEY" in text
