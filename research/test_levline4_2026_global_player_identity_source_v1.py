from __future__ import annotations

import polars as pl
import pytest

from research.levline4_2026_global_player_identity_source_v1 import (
    ALLOWED_FIELDS,
    diagnose_projection,
    project_identity_source,
)


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "gsis_id": ["00-001", "00-002"],
            "display_name": ["Alpha One", "Beta Two"],
            "common_first_name": ["Alpha", "Beta"],
            "first_name": ["Alpha", "Beta"],
            "last_name": ["One", "Two"],
            "position_group": ["QB", "DB"],
            "position": ["QB", "CB"],
            "latest_team": ["ARI", "LAC"],
            "status": ["ACT", "INA"],
            "last_season": [2026, 2026],
            "jersey_number": ["1", "2"],
        }
    )


def test_projection_excludes_team_status_and_dynamic_roster_fields() -> None:
    projected = project_identity_source(_frame())
    assert tuple(projected.columns) == ALLOWED_FIELDS
    assert "latest_team" not in projected.columns
    assert "status" not in projected.columns
    assert "last_season" not in projected.columns
    assert "jersey_number" not in projected.columns
    diagnostic = diagnose_projection(projected)
    assert diagnostic["duplicate_gsis_identity_conflicts"] == 0
    assert diagnostic["exact_display_name_collision_count"] == 0


def test_missing_identity_field_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="missing required player identity fields"):
        project_identity_source(_frame().drop("gsis_id"))


def test_exact_display_name_collision_is_descriptive_not_resolved() -> None:
    frame = pl.DataFrame(
        {
            "gsis_id": ["00-001", "00-999"],
            "display_name": ["Same Name", "Same Name"],
            "common_first_name": ["Same", "Same"],
            "first_name": ["Same", "Same"],
            "last_name": ["Name", "Name"],
            "position_group": ["QB", "DB"],
            "position": ["QB", "CB"],
        }
    )
    diagnostic = diagnose_projection(project_identity_source(frame))
    assert diagnostic["exact_display_name_collision_count"] == 1
    assert diagnostic["duplicate_gsis_identity_conflicts"] == 0
