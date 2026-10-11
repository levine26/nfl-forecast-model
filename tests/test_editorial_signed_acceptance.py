from __future__ import annotations

import csv
from hashlib import sha256
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import json
from pathlib import Path
import pytest

from scripts.editorial_signed_acceptance import (
    ClaimAcceptanceBlocked, _canonical, _digest, require_signed_claim_receipts,
    verify_signed_claim_receipts,
)

PRIVATE_SIGNER = Ed25519PrivateKey.generate()
PUBLIC_VERIFICATION_KEY = PRIVATE_SIGNER.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("utf-8")


def evidence(tmp_path: Path):
    forecast = tmp_path / "this_week.csv"
    with forecast.open("w", newline="", encoding="utf-8") as stream:
        w = csv.DictWriter(stream, fieldnames=["game_id", "gameday", "gametime", "away_team", "home_team", "final_home_prob"])
        w.writeheader()
        row = {"game_id": "2026_05_TB_DAL", "gameday": "2026-10-08", "gametime": "20:15",
               "away_team": "TB", "home_team": "DAL", "final_home_prob": "0.8169"}
        w.writerow(row)
    human = "Tampa Bay faces Dallas in a tactical line-of-scrimmage matchup."
    previews = tmp_path / "game_previews.json"
    previews.write_text(json.dumps({row["game_id"]: {"paragraphs": [human, "Model-only paragraph"],
        "reported_sources": [{"source_url": f"https://{fam}.example/report"} for fam in ("tampa", "dallas")]}}))
    sources = [
        {"publisher_family": fam, "canonical_url": f"https://{fam}.example/report",
         "article_content_sha256": sha256(fam.encode()).hexdigest(),
         "published_utc": "2026-10-07T19:00:00Z", "captured_utc": "2026-10-07T19:15:00Z",
         "original_article_content_reviewed": True}
        for fam in ("tampa", "dallas")
    ]
    rec = {
        "official_forecast_sha256": _digest(row),
        "human_paragraph_sha256": sha256(human.encode()).hexdigest(),
        "all_material_factual_clauses_reviewed": True,
        "independent_semantic_review_complete": True,
        "point_in_time_evidence_review_complete": True,
        "reviewer_id": "independent-editor-1",
        "reviewed_utc": "2026-10-10T19:00:00Z",
        "sources": sources,
        "claims": [{"statement": "Tampa Bay plays Dallas.",
                    "judgment": "verified",
                    "exact_supporting_excerpt": "Tampa Bay will visit the Dallas Cowboys for the contest on Thursday evening.",
                    "article_content_sha256": sources[0]["article_content_sha256"],
                    "independently_entails_claim": True}],
    }
    payload = {"schema_version": 1,
               "canonical_slate_sha256": sha256(forecast.read_bytes()).hexdigest(),
               "games": {row["game_id"]: rec}}
    dossier = tmp_path / "approval.json"
    sign(dossier, payload)
    return forecast, previews, dossier, payload


def sign(path: Path, payload: dict):
    path.write_text(json.dumps({"payload": payload,
                                "signature": base64.b64encode(PRIVATE_SIGNER.sign(_canonical(payload))).decode("ascii")}))


def verify(items):
    forecast, previews, dossier, _ = items
    return verify_signed_claim_receipts(forecast=forecast, previews=previews, dossier=dossier,
                                        review_public_key_pem=PUBLIC_VERIFICATION_KEY)


def test_valid_independent_pre_kickoff_attestation_is_bound_to_exact_bytes(tmp_path):
    items = evidence(tmp_path)
    assert verify(items)["games_verified_by_signed_independent_review"] == 1


def test_missing_key_or_dossier_fails_closed_even_if_provider_reports_success(tmp_path, monkeypatch):
    f, p, d, _ = evidence(tmp_path)
    with pytest.raises(ClaimAcceptanceBlocked, match="public verification key"):
        verify_signed_claim_receipts(forecast=f, previews=p, dossier=d, review_public_key_pem="")
    monkeypatch.delenv("SUNDAY_SIGNAL_REVIEW_PUBLIC_KEY", raising=False)
    with pytest.raises(ClaimAcceptanceBlocked, match="public verification key"):
        require_signed_claim_receipts(forecast=f, previews=p, dossier=d)
    with pytest.raises(ClaimAcceptanceBlocked, match="inputs missing"):
        verify_signed_claim_receipts(forecast=f, previews=p, dossier=tmp_path / "missing.json", review_public_key_pem=PUBLIC_VERIFICATION_KEY)


def test_changed_prediction_or_human_prose_invalidates_signature_provenance(tmp_path):
    items = evidence(tmp_path)
    f, p, _, _ = items
    f.write_text(f.read_text().replace("0.8169", "0.8000"))
    with pytest.raises(ClaimAcceptanceBlocked, match="canonical forecast bytes"):
        verify(items)
    items = evidence(tmp_path)
    p.write_text(p.read_text().replace("tactical", "different"))
    with pytest.raises(ClaimAcceptanceBlocked, match="HUMAN paragraph"):
        verify(items)


def test_provider_supplied_approval_flags_or_modified_dossier_cannot_self_sign(tmp_path):
    items = evidence(tmp_path)
    _, _, dossier, payload = items
    payload["games"]["2026_05_TB_DAL"]["claims"][0]["judgment"] = "contradicted"
    dossier.write_text(json.dumps({"payload": payload, "signature": "0" * 64}))
    with pytest.raises(ClaimAcceptanceBlocked, match="signature"):
        verify(items)
    sign(dossier, payload)
    with pytest.raises(ClaimAcceptanceBlocked, match="unsupported"):
        verify(items)


def test_failed_point_in_time_and_unsupported_source_receipts_are_rejected(tmp_path):
    items = evidence(tmp_path)
    _, _, d, data = items
    rec = data["games"]["2026_05_TB_DAL"]
    rec["sources"][0]["captured_utc"] = "2026-10-09T03:00:00Z"
    sign(d, data)
    with pytest.raises(ClaimAcceptanceBlocked, match="before kickoff"):
        verify(items)
    rec["sources"][0]["captured_utc"] = "2026-10-07T19:15:00Z"
    rec["claims"][0]["article_content_sha256"] = "a" * 64
    sign(d, data)
    with pytest.raises(ClaimAcceptanceBlocked, match="detached"):
        verify(items)


def test_unrelated_signed_article_cannot_cover_different_public_citation(tmp_path):
    items = evidence(tmp_path)
    _, previews, _, _ = items
    original = json.loads(previews.read_text())
    original["2026_05_TB_DAL"]["reported_sources"][0]["source_url"] = "https://unrelated.example/report"
    previews.write_text(json.dumps(original))
    with pytest.raises(ClaimAcceptanceBlocked, match="do not match public cited URLs"):
        verify(items)


def test_all_three_human_publishers_require_separate_signed_claim_review():
    repo = Path(__file__).resolve().parents[1]
    for workflow in ("groq_media_writer.yml", "chatgpt_media_ingest.yml",
                     "chatgpt_failed_game_ingest.yml"):
        text = (repo / ".github/workflows" / workflow).read_text()
        final = text.rsplit("from scripts.verify_human_source_acceptance import require_verified_human_sources", 1)[1]
        before_publish = final.split("      - name: Publish editorial-only", 1)[0]
        assert "require_verified_human_sources(status, games_expected=games)" in before_publish
        assert "from scripts.editorial_signed_acceptance import require_signed_claim_receipts" in before_publish
        assert "require_signed_claim_receipts()" in before_publish
        assert "vars.SUNDAY_SIGNAL_REVIEW_PUBLIC_KEY" in text
