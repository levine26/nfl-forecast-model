from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = [
    (".github/workflows/groq_media_writer.yml", "Publish editorial-only outputs"),
    (".github/workflows/chatgpt_media_ingest.yml", "Publish editorial-only outputs"),
]


@pytest.mark.parametrize("path,publish_step", WORKFLOWS)
def test_all_active_primary_human_writer_publication_paths_require_real_source_acceptance(
    path, publish_step,
):
    content = (ROOT / path).read_text(encoding="utf-8")
    finalization = content.split("      - name: Finalize and enforce full-slate launch gate", 1)
    assert len(finalization) == 2, f"missing final launch gate in {path}"
    before_publish = finalization[1].split(f"      - name: {publish_step}", 1)
    assert len(before_publish) == 2, f"missing publisher boundary in {path}"
    audit = before_publish[0]
    assert "python scripts/finalize_editorial.py" in audit
    assert "require_verified_human_sources(status, games_expected=games)" in audit
    assert "from scripts.verify_human_source_acceptance import require_verified_human_sources" in audit


@pytest.mark.parametrize("path,publish_step", WORKFLOWS)
def test_source_acceptance_is_after_slate_validation_and_before_main_write(path, publish_step):
    text = (ROOT / path).read_text(encoding="utf-8")
    before_publish, after_publish = text.split(f"      - name: {publish_step}", 1)
    final_launch = before_publish.rsplit("      - name: Finalize and enforce full-slate launch gate", 1)[1]
    gate_location = final_launch.index("require_verified_human_sources(status, games_expected=games)")
    slate_location = final_launch.index("if finalizer.get('status') != 'healthy'")
    assert slate_location < gate_location
    assert "git push origin HEAD:main" in after_publish
