from __future__ import annotations

from pathlib import Path
import pytest

from scripts.verify_human_source_acceptance import (
    SourceAcceptanceBlocked,
    require_verified_human_sources,
)


def _status():
    return {
        "editorial_acceptance": {
            "status": "healthy",
            "games_expected": 15,
            "games_with_structurally_eligible_human_reads": 15,
            "games_rejected": 0,
            "article_resolution_verified": True,
            "claim_support_verified": True,
        }
    }


def test_canonical_full_slate_verified_source_audit_may_pass():
    require_verified_human_sources(_status(), games_expected=15)


@pytest.mark.parametrize("field,value,expected", [
    ("article_resolution_verified", False, "article_resolution_verified"),
    ("claim_support_verified", False, "claim_support_verified"),
    ("status", "degraded", "acceptance_status"),
    ("games_expected", 14, "audit_games_expected"),
    ("games_with_structurally_eligible_human_reads", 14, "verified_human_games"),
    ("games_rejected", 1, "games_rejected"),
])
def test_all_missing_quality_proofs_fail_closed(field, value, expected):
    status = _status()
    status["editorial_acceptance"][field] = value
    with pytest.raises(SourceAcceptanceBlocked, match=expected):
        require_verified_human_sources(status, games_expected=15)


def test_legacy_quota_recovery_is_not_automatic_source_certification():
    # Reproduces Week 5: all 15 legacy focused and two-paragraph validators
    # pass, yet neither actual article content nor claim support was verified.
    status = _status()
    status["editorial_acceptance"].update(
        status="degraded",
        article_resolution_verified=False,
        claim_support_verified=False,
        games_with_structurally_eligible_human_reads=0,
        games_rejected=15,
    )
    status["copilot_media"] = {"status": "healthy", "games_applied": 15}
    status["editorial_finalizer"] = {"status": "healthy", "games": 15}
    with pytest.raises(SourceAcceptanceBlocked, match="article_resolution_verified=false"):
        require_verified_human_sources(status, games_expected=15)


def test_missing_audit_or_wrong_slate_never_authorizes_publication():
    with pytest.raises(SourceAcceptanceBlocked, match="missing"):
        require_verified_human_sources({"copilot_media": {"status": "healthy"}}, games_expected=15)
    with pytest.raises(SourceAcceptanceBlocked, match="invalid canonical"):
        require_verified_human_sources(_status(), games_expected=0)


def test_workflow_calls_hard_gate_before_editorial_publication():
    path = Path(__file__).resolve().parents[1] / ".github/workflows/chatgpt_failed_game_ingest.yml"
    content = path.read_text(encoding="utf-8")
    final_gate = content.split("      - name: Finalize and enforce publication gate", 1)[1]
    before_publish = final_gate.split("      - name: Publish editorial-only recovery", 1)[0]
    assert "require_verified_human_sources(status, games_expected=games)" in before_publish
    assert "tests/test_verified_human_source_gate.py" in content


def test_source_gate_reports_every_game_level_rejection_in_one_failure():
    status = _status()
    status["editorial_acceptance"].update(
        status="degraded",
        article_resolution_verified=False,
        claim_support_verified=False,
        games_with_structurally_eligible_human_reads=13,
        games_rejected=2,
        issues={
            "2026_05_CLE_NYJ": ["insufficient_tactical_action", "unverified_source_claim"],
            "2026_05_DEN_LAC": ["unverified_source_claim", "unverified_source_claim"],
        },
    )
    with pytest.raises(SourceAcceptanceBlocked) as caught:
        require_verified_human_sources(status, games_expected=15)
    message = str(caught.value)
    assert "article_resolution_verified=false" in message
    assert "claim_support_verified=false" in message
    assert "CLE_NYJ" in message and "DEN_LAC" in message
    assert "insufficient_tactical_action" in message
    # Each rejection rule is reported once per game; no fail-fast hiding.
    assert message.count("2026_05_CLE_NYJ") == 1
    assert message.count("2026_05_DEN_LAC") == 1
    assert message.count('"unverified_source_claim"') == 2


def test_missing_game_issue_map_still_fails_closed_with_diagnostic_caveat():
    status = _status()
    status["editorial_acceptance"]["claim_support_verified"] = False
    status["editorial_acceptance"]["issues"] = "invalid"
    with pytest.raises(SourceAcceptanceBlocked, match="all_game_rejection_rules=unavailable"):
        require_verified_human_sources(status, games_expected=15)
