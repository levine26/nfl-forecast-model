from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".github/workflows"


def test_one_automatic_manifest_owner_and_no_duplicate_article_sweep():
    release = (ROOT / "editorial_source_batch_shadow.yml").read_text()
    legacy = (ROOT / "research_source_provenance_shadow.yml").read_text()
    marker = '"inputs/chatgpt_media/fallback/manifest.json"'
    assert marker in release
    assert marker not in legacy
    assert "branches: [main]" in release
    assert "workflow_dispatch:" in release


def test_rolling_slate_uses_dynamic_canonical_count_not_week5_magic_number():
    workflow = (ROOT / "editorial_source_batch_shadow.yml").read_text()
    assert "a['games_expected'] > 0" in workflow
    assert "a['games_expected'] == a['games_audited']" in workflow
    assert "a['games_expected'] == a['games_audited'] == 15" not in workflow
    assert "name: week5-" not in workflow
    assert "current-slate-editorial-diagnostic-shadow-" in workflow


def test_capture_is_read_only_and_isolated_from_publication():
    workflow = (ROOT / "editorial_source_batch_shadow.yml").read_text()
    assert "contents: read" in workflow
    assert "editorial_publication_authorized" in workflow
    assert "a['games_with_independently_verified_human_reads'] == 0" in workflow
    assert "a['editorial_publication_authorized'] is False" in workflow
    assert "git push origin" not in workflow
    assert "actions/upload-artifact@v4" in workflow


def test_scheduled_shadow_checks_do_not_compete_with_pr_or_claim_exact_deadline():
    workflow = (ROOT / "editorial_source_batch_shadow.yml").read_text()
    assert '0 19 * * 3' in workflow
    assert '0 19 * * 6' in workflow
    assert '0 9 * * 0' in workflow
    assert '0 16 * * 1' in workflow
    assert "sunday-signal-source-pr-{0}" in workflow
    assert "'sunday-signal-source-production-shadow'" in workflow
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow
    assert "best effort" in workflow.lower()
