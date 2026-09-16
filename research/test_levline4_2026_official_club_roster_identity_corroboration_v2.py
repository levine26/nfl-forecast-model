from __future__ import annotations

from pathlib import Path

import polars as pl

from research.levline4_2026_official_club_roster_identity_corroboration_v2 import (
    EXACT_HEADERS,
    audit_cross_publication,
    build_week2_candidate_index,
    evaluate_gates,
    load_clubs,
    load_contract,
    normalize_jersey,
    parse_official_roster_html,
    run_validation,
    wilson_lower,
)
from research.levline4_prospective_inactive_gsis_resolver_v1 import SOURCE_FIELDS


class FakeResponse:
    def __init__(self, url: str, content: bytes):
        self.url = url
        self.status_code = 200
        self.content = content
        self.headers = {"Content-Type": "text/html; charset=utf-8"}


def make_html(rows: int = 70, *, conflicting_profile_url: bool = False) -> bytes:
    body = []
    for i in range(rows):
        second = (
            f'<a href="/team/players-roster/other-{i}/">other</a>'
            if conflicting_profile_url and i == 0
            else ""
        )
        body.append(
            "<tr>"
            f'<td><a href="/team/players-roster/player-{i}-example/" title="Player{i} Example"><img alt=""></a>'
            f'<span><a href="/team/players-roster/player-{i}-example/">Player{i} Example</a></span>{second}</td>'
            f"<td>{i}</td><td>CB</td><td>6-0</td><td>200</td><td>25</td><td>2</td><td>Example U</td>"
            "</tr>"
        )
    return (
        "<html><body><table><thead><tr>"
        + "".join(f"<th>{h}</th>" for h in EXACT_HEADERS)
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></body></html>"
    ).encode()


def test_normalize_jersey_is_deterministic():
    assert normalize_jersey("07") == "7"
    assert normalize_jersey(0) == "0"
    assert normalize_jersey(" 12 ") == "12"
    assert normalize_jersey("") == ""
    assert normalize_jersey("A") == "A"


def test_parser_accepts_duplicate_anchors_to_one_unique_profile_url():
    rows, summary = parse_official_roster_html(
        "ARI",
        "www.azcardinals.com",
        "https://www.azcardinals.com/team/players-roster/",
        "2026-09-16T18:00:00Z",
        make_html(70),
    )
    assert len(rows) == 70
    assert summary["parser_team_gate_pass"] is True
    assert summary["selected_exact_header_tables"] == 1
    assert summary["malformed_rows"] == 0
    assert rows[0]["player_name_rendered"] == "Player0 Example"
    assert rows[0]["normalized_jersey"] == "0"
    assert rows[0]["position_rendered"] == "CB"


def test_parser_rejects_two_distinct_profile_urls_in_one_row():
    rows, summary = parse_official_roster_html(
        "ARI",
        "www.azcardinals.com",
        "https://www.azcardinals.com/team/players-roster/",
        "2026-09-16T18:00:00Z",
        make_html(70, conflicting_profile_url=True),
    )
    assert len(rows) == 69
    assert summary["parser_team_gate_pass"] is False
    assert summary["malformed_rows"] == 1
    assert "unique_profile_url_count:2" in summary["errors"][0]["issue"]


def test_candidate_index_and_audit_preserve_unknown_and_ambiguity_states():
    frame = pl.DataFrame(
        [
            {"season": 2026, "game_type": "REG", "week": 2, "team": "ARI", "gsis_id": "A", "jersey_number": "7", "first_name": "Alpha", "football_name": "Alpha", "last_name": "One"},
            {"season": 2026, "game_type": "REG", "week": 2, "team": "ARI", "gsis_id": "B", "jersey_number": "8", "first_name": "Beta", "football_name": "Beta", "last_name": "Two"},
            {"season": 2026, "game_type": "REG", "week": 2, "team": "ARI", "gsis_id": "C", "jersey_number": "9", "first_name": "Same", "football_name": "Same", "last_name": "Name"},
            {"season": 2026, "game_type": "REG", "week": 2, "team": "ARI", "gsis_id": "D", "jersey_number": "10", "first_name": "Same", "football_name": "Same", "last_name": "Name"},
        ],
        schema=list(SOURCE_FIELDS),
        orient="row",
    )
    index = build_week2_candidate_index(frame)
    official = [
        {"team": "ARI", "normalized_name": "alpha one", "normalized_jersey": "7"},
        {"team": "ARI", "normalized_name": "beta two", "normalized_jersey": "99"},
        {"team": "ARI", "normalized_name": "same name", "normalized_jersey": "9"},
        {"team": "ARI", "normalized_name": "missing person", "normalized_jersey": "1"},
    ]
    audited, summary = audit_cross_publication(official, index)
    assert summary["exact_unique_week2_name_candidates"] == 2
    assert summary["jersey_auditable_rows"] == 2
    assert summary["jersey_agreement_rows"] == 1
    assert summary["jersey_disagreement_rows"] == 1
    assert summary["ambiguous_weekly_name_candidates"] == 1
    assert summary["unmatched_official_rows"] == 1
    assert [row["candidate_state"] for row in audited] == [
        "EXACT_UNIQUE", "EXACT_UNIQUE", "AMBIGUOUS_UNQUALIFIED", "UNMATCHED_UNKNOWN"
    ]


def test_wilson_lower_bound_behaves_as_frozen_gate():
    assert wilson_lower(1800, 1800) > 0.99
    assert wilson_lower(0, 0) == 0.0


def build_projection(path: Path) -> None:
    clubs, _ = load_clubs()
    records = []
    for team_index, team in enumerate(clubs):
        for i in range(70):
            records.append(
                {
                    "season": 2026,
                    "game_type": "REG",
                    "week": 2,
                    "team": team,
                    "gsis_id": f"00-{team_index:02d}{i:04d}",
                    "jersey_number": str(i),
                    "first_name": f"Player{i}",
                    "football_name": f"Player{i}",
                    "last_name": "Example",
                }
            )
    pl.DataFrame(records).select(list(SOURCE_FIELDS)).write_parquet(path)


def test_gate_function_requires_canonical_first_execution():
    contract = load_contract()
    team_summaries = [{"parser_team_gate_pass": True} for _ in range(32)]
    audit = {
        "exact_unique_week2_name_candidates": 2240,
        "exact_unique_name_coverage": 1.0,
        "jersey_auditable_rows": 2240,
        "jersey_agreement_rate": 1.0,
        "jersey_agreement_wilson95_lower": wilson_lower(2240, 2240),
    }
    good = evaluate_gates(
        team_summaries=team_summaries,
        capture_errors=[],
        audit_summary=audit,
        contract=contract,
        canonical_first_execution=True,
    )
    assert good["fresh_validation_pass"] is True
    bad = evaluate_gates(
        team_summaries=team_summaries,
        capture_errors=[],
        audit_summary=audit,
        contract=contract,
        canonical_first_execution=False,
    )
    assert bad["fresh_validation_pass"] is False


def test_full_synthetic_validation_passes_but_never_authorizes_forecast(tmp_path: Path):
    projection = tmp_path / "projection.parquet"
    build_projection(projection)

    # Synthetic fixtures must satisfy the production SHA guard only in lower-level tests;
    # full run_validation correctly refuses any non-frozen projection bytes.
    from research import levline4_2026_official_club_roster_identity_corroboration_v2 as mod

    original_sha = mod.SOURCE_PROJECTION_SHA256
    synthetic_sha = mod.sha256_bytes(projection.read_bytes())
    mod.SOURCE_PROJECTION_SHA256 = synthetic_sha
    try:
        def fake_get(url, **kwargs):
            return FakeResponse(url, make_html(70))

        receipt = run_validation(
            projection,
            tmp_path / "out",
            get=fake_get,
            canonical_first_execution=True,
        )
    finally:
        mod.SOURCE_PROJECTION_SHA256 = original_sha

    assert receipt["status"] == "PASS"
    assert receipt["captured_team_count"] == 32
    assert receipt["parsed_official_rows"] == 2240
    assert receipt["audit_summary"]["exact_unique_week2_name_candidates"] == 2240
    assert receipt["audit_summary"]["jersey_agreement_rows"] == 2240
    assert receipt["official_club_roster_identity_metadata_parser_qualified"] is True
    assert receipt["week2_exact_unique_name_plus_jersey_corroboration_rule_qualified"] is True
    for key in (
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified",
        "general_2026_player_identity_to_gsis_qualified",
        "game_day_membership_qualified",
        "availability_state_authorized",
        "player_value_join_authorized",
        "forecast_probability_effect_authorized",
        "model_fit_authorized",
        "production_authorized",
    ):
        assert receipt[key] is False
