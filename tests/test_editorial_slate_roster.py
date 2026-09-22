from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "maintain_editorial_slate_roster.py"
SPEC = importlib.util.spec_from_file_location("maintain_editorial_slate_roster", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_current(path: Path, rows: list[dict]) -> None:
    fieldnames = ["game_id", "season", "week"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_roster(path: Path, season: int, week: int, game_ids: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "season": season,
                "week": week,
                "game_ids": game_ids,
            }
        ),
        encoding="utf-8",
    )


def test_same_week_roster_never_shrinks(tmp_path: Path) -> None:
    current = tmp_path / "this_week.csv"
    roster = tmp_path / "roster.json"
    _write_current(
        current,
        [{"game_id": "2026_02_NYG_LA", "season": 2026, "week": 2}],
    )
    _write_roster(
        roster,
        2026,
        2,
        ["2026_02_CAR_ATL", "2026_02_NYG_LA"],
    )

    payload = MODULE.maintain_roster(current, roster)

    assert payload["game_ids"] == ["2026_02_CAR_ATL", "2026_02_NYG_LA"]


def test_same_week_roster_can_expand(tmp_path: Path) -> None:
    current = tmp_path / "this_week.csv"
    roster = tmp_path / "roster.json"
    _write_current(
        current,
        [
            {"game_id": "2026_02_NYG_LA", "season": 2026, "week": 2},
            {"game_id": "2026_02_IND_KC", "season": 2026, "week": 2},
        ],
    )
    _write_roster(roster, 2026, 2, ["2026_02_NYG_LA"])

    payload = MODULE.maintain_roster(current, roster)

    assert payload["game_ids"] == ["2026_02_NYG_LA", "2026_02_IND_KC"]


def test_roster_rolls_forward_on_new_week(tmp_path: Path) -> None:
    current = tmp_path / "this_week.csv"
    roster = tmp_path / "roster.json"
    _write_current(
        current,
        [
            {"game_id": "2026_03_ARI_SEA", "season": 2026, "week": 3},
            {"game_id": "2026_03_LA_SF", "season": 2026, "week": 3},
        ],
    )
    _write_roster(roster, 2026, 2, ["2026_02_NYG_LA"])

    payload = MODULE.maintain_roster(current, roster)

    assert payload["season"] == 2026
    assert payload["week"] == 3
    assert payload["game_ids"] == ["2026_03_ARI_SEA", "2026_03_LA_SF"]


def test_empty_current_preserves_existing_roster(tmp_path: Path) -> None:
    current = tmp_path / "this_week.csv"
    roster = tmp_path / "roster.json"
    _write_current(current, [])
    _write_roster(
        roster,
        2026,
        2,
        ["2026_02_CAR_ATL", "2026_02_NYG_LA"],
    )

    payload = MODULE.maintain_roster(current, roster)

    assert payload["week"] == 2
    assert payload["game_ids"] == ["2026_02_CAR_ATL", "2026_02_NYG_LA"]
