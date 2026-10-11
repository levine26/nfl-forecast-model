from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ingest_chatgpt_failed_games.py"
spec = importlib.util.spec_from_file_location("ingest_chatgpt_failed_games", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _status() -> dict:
    return {
        "groq_provider_fallback": {
            "run_id": "42",
            "status": "degraded",
            "games": {
                "g1": {
                    "provider_result": "failed",
                    "fallback_source": "last_validated_editorial",
                    "requires_chatgpt_refresh": True,
                },
                "g2": {
                    "provider_result": "success",
                    "requires_chatgpt_refresh": False,
                },
            },
        }
    }


def _manifest(root: Path, game_ids: list[str], generated: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({
        "schema_version": 1,
        "producer": "chatgpt-consumer-session",
        "research_mode": "live-web-search",
        "forecast_path_identity": "F-ST-01-FROZEN-2026",
        "generated_utc": generated,
        "game_ids": game_ids,
    }))
    for gid in game_ids:
        (root / f"{gid}.json").write_text(json.dumps({"games": {gid: {"headline": gid}}}))


def test_manifest_may_target_only_failed_games_requiring_chatgpt(tmp_path: Path) -> None:
    root = tmp_path / "fallback"
    _manifest(root, ["g1"], "2026-09-12T15:30:00Z")
    targets = module.validate_fallback_manifest(
        root,
        ["g1", "g2"],
        _status(),
        now=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
    )
    assert targets == ["g1"]


def test_manifest_cannot_overwrite_successful_groq_game(tmp_path: Path) -> None:
    root = tmp_path / "fallback"
    _manifest(root, ["g2"], "2026-09-12T15:30:00Z")
    try:
        module.validate_fallback_manifest(
            root,
            ["g1", "g2"],
            _status(),
            now=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "only Groq-failed games" in str(exc)
    else:
        raise AssertionError("successful Groq game must not be replaceable by fallback")


def test_mixed_payload_replaces_only_target_game() -> None:
    base = {
        "games": {
            "g1": {
                "headline": "old failed game",
                "paragraph1": "old paragraph one",
                "paragraph2": "old paragraph two",
                "sources": [{"name": "A", "title": "A", "url": "https://www.nfl.com/news/a"}],
            },
            "g2": {
                "headline": "successful Groq game",
                "paragraph1": "successful Groq paragraph",
                "model_rationale": "Successful game keeps its matchup mechanism and remains untouched by a fallback aimed at the other matchup only.",
                "sources": [{"name": "B", "title": "B", "url": "https://www.espn.com/nfl/story/b"}],
            },
        }
    }
    chatgpt = {
        "g1": {
            "headline": "fresh ChatGPT failed-game replacement",
            "paragraph1": "fresh replacement paragraph",
            "model_rationale": "Fresh failed-game research supplies a new matchup mechanism without changing any numerical LevLine forecast input or output.",
            "sources": [{"name": "C", "title": "C", "url": "https://www.cbssports.com/nfl/c"}],
        }
    }
    mixed = module.build_mixed_raw_payload(
        canonical_game_ids=["g1", "g2"],
        base_artifact=base,
        chatgpt_entries=chatgpt,
    )
    assert mixed["games"]["g1"]["headline"].startswith("fresh ChatGPT")
    assert mixed["games"]["g2"]["headline"] == "successful Groq game"
    assert mixed["games"]["g2"]["paragraph1"] == "successful Groq paragraph"



def test_mixed_payload_recovers_missing_successful_game_from_validated_preview() -> None:
    base = {
        "games": {
            "g1": {
                "headline": "old failed game",
                "paragraph1": "old paragraph one",
                "paragraph2": "old paragraph two",
                "sources": [{"name": "A", "title": "A", "url": "https://www.nfl.com/news/a"}],
            }
        }
    }
    chatgpt = {
        "g1": {
            "headline": "fresh ChatGPT failed-game replacement",
            "paragraph1": "fresh replacement paragraph",
            "model_rationale": "Fresh failed-game research supplies a new matchup mechanism without changing any numerical LevLine forecast input or output.",
            "sources": [{"name": "C", "title": "C", "url": "https://www.cbssports.com/nfl/c"}],
        }
    }
    previews = {
        "g2": {
            "headline": "last validated successful game",
            "paragraphs": [
                "The successful game keeps its previously validated human matchup read even when a later provider publication contracts to another game only.",
                "LevLine numbers remain deterministic. The successful matchup keeps its protection and explosive-play mechanism because that prior editorial read already passed the publication validator. The pick: Team B moneyline.",
            ],
            "reported_sources": [
                {
                    "source_name": "ESPN",
                    "title": "Validated source",
                    "source_url": "https://www.espn.com/nfl/story/b",
                }
            ],
        }
    }

    mixed = module.build_mixed_raw_payload(
        canonical_game_ids=["g1", "g2"],
        base_artifact=base,
        chatgpt_entries=chatgpt,
        preview_artifact=previews,
    )

    assert mixed["games"]["g1"]["headline"].startswith("fresh ChatGPT")
    assert mixed["games"]["g2"]["headline"] == "last validated successful game"
    assert mixed["games"]["g2"]["sources"][0]["name"] == "ESPN"
    assert "protection and explosive-play mechanism" in mixed["games"]["g2"]["model_rationale"]



def test_mark_recovered_clears_refresh_requirement_only_for_target() -> None:
    updated = module.mark_chatgpt_recovered(
        _status(),
        ["g1"],
        now=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
    )
    section = updated["groq_provider_fallback"]
    assert section["games"]["g1"]["fallback_source"] == "chatgpt"
    assert section["games"]["g1"]["requires_chatgpt_refresh"] is False
    assert section["games"]["g2"]["requires_chatgpt_refresh"] is False
    assert section["status"] == "healthy"
    assert section["failed_games"] == []



def test_mixed_payload_bootstraps_successful_game_from_validated_groq_checkpoint() -> None:
    base = {"games": {}}
    chatgpt = {
        "g1": {
            "headline": "fresh failed-game replacement",
            "paragraph1": "fresh replacement paragraph",
            "model_rationale": "Fresh failed-game research supplies a matchup mechanism while leaving the successful provider game untouched and preserving its human editorial authority.",
            "sources": [{"name": "CBS", "title": "Report", "url": "https://www.cbssports.com/nfl/report"}],
        }
    }
    checkpoints = {
        "g2": {
            "headline": "validated Groq success",
            "paragraph1": "The successful Groq game keeps its validated matchup reporting and human prose across the weekly rollover recovery path.",
            "model_rationale": "Protection and coverage interactions remain the central football mechanism for this successful provider game, so its validated human read stays authoritative.",
            "sources": [{"name": "ESPN", "title": "Report", "url": "https://www.espn.com/nfl/story/report"}],
        }
    }

    mixed = module.build_mixed_raw_payload(
        canonical_game_ids=["g1", "g2"],
        base_artifact=base,
        chatgpt_entries=chatgpt,
        checkpoint_entries=checkpoints,
    )

    assert mixed["games"]["g1"]["headline"] == "fresh failed-game replacement"
    assert mixed["games"]["g2"]["headline"] == "validated Groq success"
    assert mixed["games"]["g2"]["paragraph1"].startswith("The successful Groq game")


def test_mixed_payload_fails_closed_when_successful_game_has_no_provider_authority() -> None:
    try:
        module.build_mixed_raw_payload(
            canonical_game_ids=["g1", "g2"],
            base_artifact={"games": {}},
            chatgpt_entries={
                "g1": {
                    "headline": "failed-game replacement",
                    "paragraph1": "replacement",
                    "model_rationale": "The failed game has a qualitative football rationale that is long enough for the strict publication contract to accept.",
                    "sources": [{"name": "NFL", "title": "Report", "url": "https://www.nfl.com/news/report"}],
                }
            },
            preview_artifact={
                "g2": {
                    "headline": "deterministic preview",
                    "paragraphs": ["preview one", "preview two"],
                    "reported_sources": [
                        {"source_name": "ESPN", "title": "Report", "source_url": "https://www.espn.com/nfl/story/report"}
                    ],
                }
            },
            checkpoint_entries={},
        )
    except ValueError as exc:
        assert "missing both published HUMAN prose and a validated Groq checkpoint" in str(exc)
    else:
        raise AssertionError("successful Groq games must fail closed rather than downgrade to preview prose")


def test_idle_historical_fallback_is_not_republished_without_active_groq_failures():
    """Do not re-ingest a prior week's manifest when current Groq is healthy."""
    from pathlib import Path

    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows"
                / "chatgpt_failed_game_ingest.yml").read_text()
    assert "from scripts.ingest_chatgpt_failed_games import _failure_targets" in workflow
    assert "if not targets.issubset(canonical):" in workflow
    assert "Missing authoritative Groq failure-state map" in workflow
    assert "No Groq failures requiring ChatGPT recovery" in workflow
    required_gate = "if: github.event_name != 'pull_request' && steps.fallback_activity.outputs.active == 'true'"
    assert workflow.count(required_gate) == 9
    assert "python scripts/ingest_chatgpt_failed_games.py" in workflow
    assert 'fallback manifest contains a game outside the canonical slate' in (
        Path(__file__).resolve().parents[1] / "scripts" / "ingest_chatgpt_failed_games.py"
    ).read_text()


def test_recovery_validates_entire_slate_and_preserves_accepted_games(tmp_path, monkeypatch):
    """Two rejected games must not suppress evaluation of the other thirteen."""
    import subprocess

    targets = [f"2026_05_TEST_{i:02d}" for i in range(15)]
    failures = {targets[4], targets[10]}
    inputs = tmp_path / "inputs"
    accepted = tmp_path / "work" / "accepted"
    inputs.mkdir()
    accepted.mkdir(parents=True)
    for gid in targets:
        (inputs / f"{gid}.json").write_text(json.dumps({
            "games": {gid: {"headline": f"Game {gid}", "paragraph1": "verified"}}
        }))
    visited = []

    def fake_validator(command, **kwargs):
        gid = command[command.index("--game-id") + 1]
        visited.append(gid)
        if gid in failures:
            raise subprocess.CalledProcessError(
                1, command,
                stderr=f"Focused editorial game validation failed: {gid}: "
                       "editorial quality: no concrete tactical action-and-counteraction explanation",
            )
        return subprocess.CompletedProcess(command, 0, stdout=f"validated {gid}")

    monkeypatch.setattr(module.subprocess, "run", fake_validator)
    report_path = tmp_path / "diagnostics.json"
    try:
        module._validate_recovery_targets(
            repo_root=tmp_path,
            input_root=inputs,
            prediction_path=tmp_path / "predictions.csv",
            accepted=accepted,
            targets=targets,
            report_path=report_path,
        )
    except ValueError as exc:
        assert "2/15 games" in str(exc)
    else:
        raise AssertionError("incomplete slate must not pass")

    report = json.loads(report_path.read_text())
    assert visited == targets
    assert report["games_accepted"] == 13
    assert report["games_rejected"] == 2
    assert report["publication_authorized"] is False
    assert {path.stem for path in accepted.glob("*.txt")} == set(targets) - failures
    for gid in failures:
        detail = report["games"][gid]
        assert detail["state"] == "rejected"
        assert detail["errors"][0]["game_id"] == gid
        assert detail["errors"][0]["suggested_repair_category"] == "editorial_quality"
        assert "tactical action-and-counteraction" in detail["errors"][0]["rejection_reason"]


def test_recovery_success_keeps_game_ownership_and_report_locked_until_slate_gate(tmp_path, monkeypatch):
    import subprocess

    targets = ["2026_05_A_B", "2026_05_C_D"]
    inputs = tmp_path / "inputs"
    accepted = tmp_path / "work" / "accepted"
    inputs.mkdir()
    accepted.mkdir(parents=True)
    for gid in targets:
        (inputs / f"{gid}.json").write_text(json.dumps({
            "games": {gid: {"headline": gid, "paragraph1": "valid distinct read"}}
        }))

    def fake_validator(command, **kwargs):
        gid = command[command.index("--game-id") + 1]
        accepted_dir = Path(command[command.index("--accepted-dir") + 1])
        assert set(path.stem for path in accepted_dir.glob("*.txt")).issubset(set(targets))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(module.subprocess, "run", fake_validator)
    report_path = tmp_path / "diagnostics.json"
    accepted_games = module._validate_recovery_targets(
        repo_root=tmp_path,
        input_root=inputs,
        prediction_path=tmp_path / "predictions.csv",
        accepted=accepted,
        targets=targets,
        report_path=report_path,
    )
    assert list(accepted_games) == targets
    assert set(path.stem for path in accepted.glob("*.txt")) == set(targets)
    report = json.loads(report_path.read_text())
    assert report["games_rejected"] == 0
    assert report["publication_authorized"] is False  # Only full-slate validation unlocks publication.


def test_recovery_error_classifier_reports_source_and_identity_separately():
    gid = "2026_05_A_B"
    errors = module._recovery_error_records(
        gid,
        "Focused editorial game validation failed: "
        f"{gid}: source URL is not a direct approved article/report: https://example.com; "
        f"{gid}: paragraph1 must discuss both teams",
    )
    assert len(errors) == 2
    assert [e["suggested_repair_category"] for e in errors] == [
        "source_research", "factual_or_identity"
    ]


def test_partial_recovery_status_retains_only_active_unresolved_game_ids():
    status = _status()
    status["groq_provider_fallback"]["games"]["g3"] = {
        "provider_result": "failed",
        "requires_chatgpt_refresh": True,
        "fallback_source": "missing",
    }
    status["groq_provider_fallback"]["failed_games"] = ["g1", "g3"]
    result = module.mark_chatgpt_recovered(
        status,
        ["g1"],
        now=datetime(2026, 9, 12, 16, tzinfo=timezone.utc),
    )
    section = result["groq_provider_fallback"]
    assert section["status"] == "degraded"
    assert section["failed_games"] == ["g3"]
    assert module._failure_targets(result) == {"g3"}
    assert status["groq_provider_fallback"]["failed_games"] == ["g1", "g3"]  # input untouched
    completed = module.mark_chatgpt_recovered(
        result,
        ["g3"],
        now=datetime(2026, 9, 12, 17, tzinfo=timezone.utc),
    )
    assert completed["groq_provider_fallback"]["failed_games"] == []
    assert completed["groq_provider_fallback"]["status"] == "healthy"
    assert module._failure_targets(completed) == set()


def test_unpersisted_provider_success_is_an_authority_gap_not_a_groq_failure(tmp_path):
    status = _status()
    base = {"games": {
        "g1": {
            "headline": "Accepted provider headline",
            "paragraph1": "a researched and previously accepted tactical explanation",
            "model_rationale": "A valid football mechanism links pressure to routes and third downs.",
            "sources": [{"name": "NFL", "title": "Report", "url": "https://www.nfl.com/news/example"}],
        }
    }}
    missing = module.missing_accepted_editorial_authority(
        canonical_game_ids=["g1", "g2", "g3"],
        status=status,
        base_artifact=base,
        checkpoint_entries={},
        preview_artifact={"g3": {"headline": "generic context", "paragraphs": ["fallback", "formula"]}},
        strict_bootstrap=True,
    )
    assert missing == {"g2", "g3"}
    assert module._failure_targets(status) == {"g1"}
    # Explicitly allow only a demonstrated gap, not every provider success.
    root = tmp_path / "fallback"
    _manifest(root, ["g2"], "2026-09-12T15:30:00Z")
    assert module.validate_fallback_manifest(
        root, ["g1", "g2", "g3"], status,
        missing_accepted_authority=missing,
        now=datetime(2026, 9, 12, 16, tzinfo=timezone.utc),
    ) == ["g2"]


def test_missing_authority_cannot_override_an_existing_validated_groq_checkpoint(tmp_path):
    status = _status()
    checkpoint = {
        "headline": "Persisted Groq headline",
        "paragraph1": "A credible specific football tactical interaction for both opponents.",
        "model_rationale": "Coverage adjustments and pressure timing shape offensive choices from drive to drive, forcing quarterbacks to respond with protection shifts, quick releases, and disciplined route timing.",
        "sources": [{"name": "NFL", "title": "Report", "url": "https://www.nfl.com/news/example"}],
    }
    gaps = module.missing_accepted_editorial_authority(
        canonical_game_ids=["g1", "g2"],
        status=status, base_artifact={"games": {}},
        checkpoint_entries={"g2": checkpoint},
        preview_artifact={},
        strict_bootstrap=True,
    )
    assert "g2" not in gaps
    root = tmp_path / "fallback"
    _manifest(root, ["g2"], "2026-09-12T15:30:00Z")
    with __import__("pytest").raises(ValueError, match="only Groq-failed games"):
        module.validate_fallback_manifest(
            root, ["g1", "g2"], status, missing_accepted_authority=gaps,
            now=datetime(2026, 9, 12, 16, tzinfo=timezone.utc),
        )


def test_recovered_missing_editorial_authority_preserves_true_provider_outcome():
    old = _status()
    repaired = module.mark_chatgpt_recovered(
        old, ["g2"], missing_authority_recovered={"g2"},
        now=datetime(2026, 9, 12, 16, tzinfo=timezone.utc),
    )
    original = repaired["groq_provider_fallback"]["games"]["g2"]
    assert original["provider_result"] == "success"
    assert original["editorial_recovery_reason"] == "missing_accepted_human_authority"
    assert original["fallback_source"] == "chatgpt"
    assert original["requires_chatgpt_refresh"] is False
    # Do not clear the other game, which still genuinely needs failed-Groq recovery.
    assert repaired["groq_provider_fallback"]["failed_games"] == ["g1"]
    assert repaired["groq_provider_fallback"]["status"] == "degraded"
    assert old["groq_provider_fallback"]["games"]["g2"] == {
        "provider_result": "success", "requires_chatgpt_refresh": False,
    }


def test_deterministic_preview_is_not_human_authority_in_same_week_mode():
    status = _status()
    gaps = module.missing_accepted_editorial_authority(
        canonical_game_ids=["g1", "g2"], status=status,
        base_artifact={"games": {}}, checkpoint_entries={},
        preview_artifact={"g2": {
            "headline": "Stock deterministic preview",
            "paragraphs": ["A generic football paragraph", "A deterministic model paragraph"],
            "reported_sources": [{"name": "NFL", "title": "Report", "url": "https://www.nfl.com/news/a"}],
            "editorial_voice": {"copilot_researched": False},
        }},
        strict_bootstrap=False,
    )
    assert gaps == {"g2"}
