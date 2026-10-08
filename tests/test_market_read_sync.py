from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from nfl_forecast.editorial_model_read import render_model_paragraph
from scripts.sync_market_reads import ReadSyncError, synchronize_reads, synchronize_file


NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)


def row(gid: str = "2026_05_CHI_GB", **overrides) -> dict:
    source = dict(
        game_id=gid, season="2026", week="5", gameday="2026-10-11",
        gametime="13:00", away_team="CHI", home_team="GB", pick="CHI",
        final_home_prob="0.40", fst_pure_home_prob="0.36",
        pure_home_prob="0.34", market_home_prob="0.43",
        margin_sigma="12.9", expected_total="44.0",
        expected_margin="-1.8", spread_line="-2.5",
        model_version="0.9.0-fst",
        fst_artifact_id="F-ST-01-FROZEN-2026",
        final_probability_strategy="F-ST-01-FROZEN-2026",
        prediction_timestamp_utc="2026-10-07T11:00:00+00:00",
        market_snapshot_timestamp_utc="2026-10-07T10:58:00+00:00",
    )
    source.update(overrides)
    return source


def preview(source: dict) -> dict:
    return dict(
        headline="Human: the big injury story",
        paragraphs=["Human first paragraph. Unique and sourced.",
                    render_model_paragraph(source, "Football context: Secondary matchup")],
        reported_sources=[{"source_name": "ESPN", "source_url": "https://espn.com/story"}],
        editorial_voice={"copilot_researched": True, "two_paragraph_contract": True},
        case_for_pick="Preserve original context",
    )


def sync(rows: list[dict], previews: dict, official: list[dict] | None = None):
    return synchronize_reads(rows, official or [], previews, now_utc=NOW)


def test_market_only_refresh_changes_only_deterministic_paragraph():
    previous = row()
    original = preview(previous)
    updated_row = row(final_home_prob="0.441", market_home_prob="0.49", spread_line="-1.0")
    result, changed = sync([updated_row], {previous["game_id"]: original})
    actual = result[previous["game_id"]]
    assert changed == 1
    assert {k: v for k, v in actual.items() if k != "paragraphs"} == {
        k: v for k, v in original.items() if k != "paragraphs"
    }
    assert actual["paragraphs"][0] == original["paragraphs"][0]
    p = actual["paragraphs"][1]
    assert p == render_model_paragraph(updated_row, "Football context: Secondary matchup")
    assert "55.9%" in p and "64.0%" in p and "51.0%" in p
    assert "Chicago Bears" in p and "a market line of Chicago Bears -1.0" in p
    assert p.endswith("The pick: Chicago Bears moneyline.")
    assert original["paragraphs"][1] != p


def test_changed_winner_rewrites_entire_deterministic_paragraph():
    old = row()
    new = row(pick="GB", final_home_prob="0.62", market_home_prob="0.61")
    updated, changed = sync([new], {old["game_id"]: preview(old)})
    p = updated[old["game_id"]]["paragraphs"][1]
    assert changed == 1
    assert "62.0%" in p
    assert "38.0% win probability" not in p
    assert "Bears a" not in p
    assert p.endswith("The pick: Green Bay Packers moneyline.")


def test_full_slate_and_duplicate_missing_extra_guards():
    rows = [row("2026_05_CHI_GB"), row("2026_05_CIN_MIA", away_team="CIN", home_team="MIA", pick="MIA", final_home_prob="0.60")]
    previews = {r["game_id"]: preview(r) for r in rows}
    good, changed = sync(rows, previews)
    assert changed == 0 and len(good) == 2
    for invalid_rows, invalid_previews in [
        (rows + [rows[0]], previews),
        (rows, {rows[0]["game_id"]: previews[rows[0]["game_id"]]}),
        (rows, {**previews, "extra": previews[rows[0]["game_id"]]}),
    ]:
        with pytest.raises(ReadSyncError, match="missing, extra, or duplicate"):
            sync(invalid_rows, invalid_previews)


def test_locked_snapshot_cannot_be_replaced_with_later_market_value():
    locked = row(
        final_home_prob="0.40", lock_status="LOCKED",
        gameday="2026-10-08", gametime="20:15",
        lock_timestamp_utc="2026-10-08T22:15:00+00:00",
    )
    later = row(final_home_prob="0.71", pick="GB", gameday="2026-10-08", gametime="20:15")
    with pytest.raises(ReadSyncError, match="authoritative locked"):
        sync([later], {later["game_id"]: preview(later)}, official=[locked])
    original = preview(locked)
    updated, count = sync([locked], {locked["game_id"]: original}, official=[locked])
    assert count == 0 and updated[locked["game_id"]]["paragraphs"] == original["paragraphs"]


def test_failure_isolation_and_no_partial_file_write(tmp_path):
    import csv
    first = row()
    second = row("2026_05_CIN_MIA", away_team="CIN", home_team="MIA", pick="MIA", final_home_prob="0.60")
    newer = row(final_home_prob="0.42")
    originals = {first["game_id"]: preview(first), second["game_id"]: preview(second)}
    originals[second["game_id"]]["paragraphs"] = ["only one"]
    for path, entries in [("this_week.csv", [newer, second]), ("prediction_history.csv", [])]:
        with (tmp_path / path).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(first) + ["lock_status"])
            writer.writeheader()
            writer.writerows(entries)
    source = json.dumps(originals, sort_keys=True)
    (tmp_path / "game_previews.json").write_text(source)
    with pytest.raises(ReadSyncError, match="exactly two"):
        synchronize_file(tmp_path)
    assert (tmp_path / "game_previews.json").read_text() == source


def test_idempotence_repeated_refresh_leaves_json_and_attribution_unchanged():
    old = row()
    original = preview(old)
    previews, changed = sync([old], {old["game_id"]: original})
    twice, again = sync([old], deepcopy(previews))
    assert changed == again == 0
    assert twice == previews
    assert twice[old["game_id"]]["reported_sources"] == original["reported_sources"]


def test_composer_contract_includes_model_artifact_public_bridge_and_score():
    original = row()
    item = preview(original)
    fresh, n = sync([original], {original["game_id"]: item})
    assert n == 0
    paragraph = fresh[original["game_id"]]["paragraphs"][1]
    assert "frozen F-ST engine" in paragraph
    assert "probability-implied presentation line" in paragraph
    assert "approximate coherent score" in paragraph
    assert "fixed arithmetic blend" in paragraph
    assert paragraph.count("The pick:") == 1


def test_missing_model_provenance_is_rejected():
    old = row()
    with pytest.raises(ReadSyncError, match="frozen model version/artifact"):
        sync([row(model_version="")], {old["game_id"]: preview(old)})


def _fixture_publisher(tmp_path, initial=None):
    import pandas as pd
    from types import SimpleNamespace
    from nfl_forecast.publish import write_outputs

    source = initial or row()
    gid = source["game_id"]
    human = preview(source)
    (tmp_path / "game_previews.json").write_text(json.dumps({gid: human}, sort_keys=True))
    games = pd.DataFrame([{"game_id": gid, "home_team": source["home_team"],
                          "away_team": source["away_team"], "home_score": None, "away_score": None}])
    def publish(current):
        write_outputs(SimpleNamespace(predictions=pd.DataFrame([current]), games=games),
                      tmp_path, now_utc=NOW)
    return publish, gid, human


def test_shared_publisher_daily_refresh_rebuilds_read_without_replacing_human(tmp_path):
    publish, gid, original = _fixture_publisher(tmp_path)
    publish(row())
    publish(row(final_home_prob="0.438", market_home_prob="0.51", spread_line="-1.0",
                prediction_timestamp_utc="2026-10-07T11:10:00+00:00"))
    result = json.loads((tmp_path / "game_previews.json").read_text())[gid]
    assert result["headline"] == original["headline"]
    assert result["reported_sources"] == original["reported_sources"]
    assert result["editorial_voice"] == original["editorial_voice"]
    assert result["paragraphs"][0] == original["paragraphs"][0]
    assert "56.2% win probability" in result["paragraphs"][1]
    assert "49.0% vig-free market signal" in result["paragraphs"][1]
    assert "a market line of Chicago Bears -1.0" in result["paragraphs"][1]
    assert result["paragraphs"][1].endswith("The pick: Chicago Bears moneyline.")
    assert synchronize_file(tmp_path, check=True) == 0


def test_shared_publisher_market_refresh_and_idempotence(tmp_path):
    publish, gid, original = _fixture_publisher(tmp_path)
    publish(row())
    publish(row(final_home_prob="0.42", market_home_prob="0.48"))
    second = (tmp_path / "game_previews.json").read_bytes()
    publish(row(final_home_prob="0.42", market_home_prob="0.48"))
    assert (tmp_path / "game_previews.json").read_bytes() == second
    assert "58.0% win probability" in json.loads(second)[gid]["paragraphs"][1]
    assert synchronize_file(tmp_path, check=True) == 0


def test_shared_publisher_fails_closed_for_missing_or_malformed_previews(tmp_path):
    import pandas as pd
    from types import SimpleNamespace
    from nfl_forecast.publish import write_outputs

    current = row()
    games = pd.DataFrame([{"game_id": current["game_id"], "home_team": "GB", "away_team": "CHI"}])
    with pytest.raises(ReadSyncError, match="missing editorial preview"):
        write_outputs(SimpleNamespace(predictions=pd.DataFrame([current]), games=games),
                      tmp_path, now_utc=NOW)
    (tmp_path / "game_previews.json").write_text(json.dumps({current["game_id"]: {
        "headline": "Human", "paragraphs": ["Only one paragraph"]
    }}))
    with pytest.raises(ReadSyncError, match="exactly two"):
        write_outputs(SimpleNamespace(predictions=pd.DataFrame([current]), games=games),
                      tmp_path, now_utc=NOW)


def test_public_deployment_check_rejects_stale_read_without_repair(tmp_path):
    import csv
    base = row()
    newer = row(final_home_prob="0.433", spread_line="-3.0")
    with (tmp_path / "this_week.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(newer))
        writer.writeheader()
        writer.writerow(newer)
    with (tmp_path / "prediction_history.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(newer))
        writer.writeheader()
    old = json.dumps({base["game_id"]: preview(base)}, sort_keys=True)
    (tmp_path / "game_previews.json").write_text(old)
    with pytest.raises(ReadSyncError, match="disagree with canonical"):
        synchronize_file(tmp_path, check=True)
    assert (tmp_path / "game_previews.json").read_text() == old


def test_market_workflow_and_daily_workflow_both_protect_commit(monkeypatch):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name in ("weekly.yml", "market_refresh.yml", "pregame.yml"):
        content = (root / ".github" / "workflows" / name).read_text()
        assert "sync_market_reads.py" in content or name == "weekly.yml"
        assert "git add outputs/" in content
    publisher = (root / "src" / "nfl_forecast" / "publish.py").read_text()
    assert "synchronize_file(out)" in publisher
    dashboard = (root / ".github" / "workflows" / "dashboard.yml").read_text()
    assert "sync_market_reads --output-dir site/public/data --check" in dashboard
    assert "sync_market_reads --output-dir site/public/data --write" not in dashboard


def test_unvalidated_context_rebase_forbidden_and_editorial_publishers_check():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    for name in ("context.yml", "groq_media_writer.yml",
                 "chatgpt_media_ingest.yml", "chatgpt_failed_game_ingest.yml"):
        content = (root / name).read_text()
        assert "sync_market_reads --output-dir outputs --check" in content
        assert "sync_market_reads --output-dir outputs --write" in content
    assert "git pull --rebase origin main" not in (root / "context.yml").read_text()
