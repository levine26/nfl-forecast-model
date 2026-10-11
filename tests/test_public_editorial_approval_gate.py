from __future__ import annotations

import csv
import json
from pathlib import Path

import scripts.gate_public_editorial_copy as gate


def files(tmp_path):
    forecast = tmp_path / "this_week.csv"
    with forecast.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["game_id", "pick", "final_home_prob"])
        w.writeheader()
        w.writerow({"game_id": "2026_05_TB_DAL", "pick": "DAL", "final_home_prob": "0.8169"})
    previews = tmp_path / "game_previews.json"
    previews.write_text('{"2026_05_TB_DAL": {"paragraphs": ["HUMAN", "MODEL"]}}')
    source = {
        "status": "healthy",
        "editorial_acceptance": {
            "status": "healthy", "games_expected": 1,
            "games_with_structurally_eligible_human_reads": 1,
            "games_rejected": 0,
            "article_resolution_verified": True,
            "claim_support_verified": True,
        },
    }
    status = tmp_path / "context_source_status.json"
    status.write_text(json.dumps(source))
    dossier = tmp_path / "approval.json"
    return status, forecast, previews, dossier


def test_forged_healthy_editorial_status_is_masked_when_signature_missing(tmp_path, monkeypatch):
    status, forecast, previews, dossier = files(tmp_path)
    forecast_before = forecast.read_bytes()
    previews_before = previews.read_bytes()
    monkeypatch.delenv("SUNDAY_SIGNAL_REVIEW_PUBLIC_KEY", raising=False)
    result = gate.gate_site_editorial_copy(status_path=status, forecast=forecast,
                                          previews=previews, dossier=dossier)
    after = json.loads(status.read_text())
    assert result["independently_verified_human_read_publication"] is False
    assert after["editorial_acceptance"]["claim_support_verified"] is False
    assert after["editorial_acceptance"]["article_resolution_verified"] is False
    assert after["status"] == "healthy"  # numeric data retains its own health
    assert forecast.read_bytes() == forecast_before
    assert previews.read_bytes() == previews_before


def test_trusted_release_remains_eligible_when_both_gates_pass(tmp_path, monkeypatch):
    status, forecast, previews, dossier = files(tmp_path)
    monkeypatch.setattr(gate, "require_signed_claim_receipts", lambda **kwargs: {"verified": True})
    result = gate.gate_site_editorial_copy(status_path=status, forecast=forecast,
                                          previews=previews, dossier=dossier)
    assert result["independently_verified_human_read_publication"] is True
    assert json.loads(status.read_text())["editorial_acceptance"]["claim_support_verified"] is True


def test_bad_or_missing_structural_gate_also_masks_publisher_booleans(tmp_path):
    status, forecast, previews, dossier = files(tmp_path)
    status.write_text('{"editorial_acceptance": {"status": "healthy"}}')
    result = gate.gate_site_editorial_copy(status_path=status, forecast=forecast,
                                          previews=previews, dossier=dossier)
    assert result["independently_verified_human_read_publication"] is False


def test_pages_pipeline_enforces_verification_on_site_copy():
    repo = Path(__file__).resolve().parents[1]
    script = (repo / ".github/workflows/dashboard.yml").read_text()
    assert "scripts/gate_public_editorial_copy.py" in script
    assert "vars.SUNDAY_SIGNAL_REVIEW_PUBLIC_KEY" in script
    assert script.index("scripts/gate_public_editorial_copy.py") < script.index(
        "npm run build"
    )
