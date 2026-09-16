from __future__ import annotations

"""Deterministic research-only parser for official NFL inactive-report articles.

This module extracts team + rendered player name + position + emergency-third-QB annotation.
It deliberately does not resolve GSIS identity, estimate availability probabilities, attach
player value, or alter a forecast.
"""

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

SCHEMA_VERSION = "levline-inactive-article-player-parser-v1"

TEAM_HEADING_TO_ABBR = {
    "CARDINALS": "ARI",
    "FALCONS": "ATL",
    "RAVENS": "BAL",
    "BILLS": "BUF",
    "PANTHERS": "CAR",
    "BEARS": "CHI",
    "BENGALS": "CIN",
    "BROWNS": "CLE",
    "COWBOYS": "DAL",
    "BRONCOS": "DEN",
    "LIONS": "DET",
    "PACKERS": "GB",
    "TEXANS": "HOU",
    "COLTS": "IND",
    "JAGUARS": "JAX",
    "CHIEFS": "KC",
    "RAIDERS": "LV",
    "CHARGERS": "LAC",
    "RAMS": "LAR",
    "DOLPHINS": "MIA",
    "VIKINGS": "MIN",
    "PATRIOTS": "NE",
    "SAINTS": "NO",
    "GIANTS": "NYG",
    "JETS": "NYJ",
    "EAGLES": "PHI",
    "STEELERS": "PIT",
    "49ERS": "SF",
    "SEAHAWKS": "SEA",
    "BUCCANEERS": "TB",
    "TITANS": "TEN",
    "COMMANDERS": "WAS",
}

EMERGENCY_RE = re.compile(r"\s*\(\s*emergency\s+third\s+QB\s*\)\s*$", re.IGNORECASE)
POSITION_RE = re.compile(r"^(?P<position>[A-Za-z][A-Za-z/.-]*)\s+(?P<name>.+?)\s*$")
HEADING_TAGS = {"h2", "h3", "h4"}


@dataclass(frozen=True)
class ParsedInactiveArticle:
    rows: list[dict[str, Any]]
    audit: dict[str, Any]


def _text(tag: Tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def _heading_team(tag: Tag) -> str | None:
    if tag.name not in HEADING_TAGS:
        return None
    normalized = _text(tag).strip().upper()
    return TEAM_HEADING_TO_ABBR.get(normalized)


def _first_list_before_next_heading(heading: Tag) -> Tag | None:
    """Return the inactive list owned by a team heading.

    NFL articles place each team's inactive list immediately after its team heading. Game
    metadata such as WHERE/WHEN appears *after* the preceding team's list and before the next
    team heading. Scoping extraction to the first list before the next heading prevents those
    metadata list items from being misclassified as players while preserving the frozen
    player-count/source-shape gates.
    """

    for element in heading.next_elements:
        if element is heading:
            continue
        if not isinstance(element, Tag):
            continue
        if element.name in HEADING_TAGS:
            return None
        if element.name == "ul":
            return element
    return None


def parse_inactive_article_html(
    raw_html: bytes | str,
    *,
    source_url: str,
    captured_at_utc: str,
    raw_html_sha256: str | None = None,
) -> ParsedInactiveArticle:
    if isinstance(raw_html, bytes):
        raw_bytes = raw_html
        html = raw_html.decode("utf-8", errors="replace")
    else:
        html = str(raw_html)
        raw_bytes = html.encode("utf-8")

    observed_sha = hashlib.sha256(raw_bytes).hexdigest()
    if raw_html_sha256 is not None and observed_sha != str(raw_html_sha256).lower():
        raise ValueError(
            f"raw HTML SHA mismatch: expected {raw_html_sha256}, observed {observed_sha}"
        )

    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    duplicate_team_sections: list[str] = []
    unparseable_entries: list[dict[str, str]] = []
    seen_teams: set[str] = set()

    for heading in soup.find_all(list(HEADING_TAGS)):
        if not isinstance(heading, Tag):
            continue
        team = _heading_team(heading)
        if team is None:
            continue

        inactive_list = _first_list_before_next_heading(heading)
        if inactive_list is None:
            # A matching navigation/sidebar heading without an owned list is not a player section.
            continue

        section_entries: list[dict[str, Any]] = []
        seen_player_keys: set[str] = set()
        duplicate_players: list[str] = []

        for element in inactive_list.find_all("li"):
            if not isinstance(element, Tag):
                continue
            entry_text = _text(element)
            if not entry_text:
                continue
            emergency_third_qb = bool(EMERGENCY_RE.search(entry_text))
            clean_text = EMERGENCY_RE.sub("", entry_text).strip()
            match = POSITION_RE.match(clean_text)
            if not match:
                unparseable_entries.append({"team": team, "text": entry_text})
                continue
            position = match.group("position").strip()
            player_name = match.group("name").strip()
            if not player_name:
                unparseable_entries.append({"team": team, "text": entry_text})
                continue

            player_key = player_name.casefold()
            if player_key in seen_player_keys:
                duplicate_players.append(player_name)
                continue
            seen_player_keys.add(player_key)
            section_entries.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "team": team,
                    "position_rendered": position,
                    "player_name_rendered": player_name,
                    "emergency_third_qb": emergency_third_qb,
                    "source_url": source_url,
                    "source_known_by_utc": captured_at_utc,
                    "source_timestamp_basis": "captured_at",
                    "raw_html_sha256": observed_sha,
                    "research_only": True,
                    "player_identity_to_gsis_qualified": False,
                    "availability_probability_feature_authorized": False,
                    "player_value_join_authorized": False,
                    "forecast_probability_effect_authorized": False,
                    "production_authorized": False,
                    "completed_2026_outcomes_used": 0,
                }
            )

        if not section_entries:
            continue
        if team in seen_teams:
            duplicate_team_sections.append(team)
        seen_teams.add(team)
        if duplicate_players:
            raise ValueError(f"duplicate player(s) within {team}: {sorted(duplicate_players)}")
        rows.extend(section_entries)

    if duplicate_team_sections:
        raise ValueError(f"duplicate team sections: {sorted(set(duplicate_team_sections))}")
    if unparseable_entries:
        raise ValueError(f"unparseable inactive entries: {unparseable_entries[:10]}")

    counts: dict[str, int] = {}
    emergency = 0
    for row in rows:
        team = str(row["team"])
        counts[team] = counts.get(team, 0) + 1
        emergency += int(bool(row["emergency_third_qb"]))

    audit = {
        "schema_version": SCHEMA_VERSION,
        "raw_html_sha256": observed_sha,
        "source_url": source_url,
        "source_known_by_utc": captured_at_utc,
        "source_timestamp_basis": "captured_at",
        "team_sections": len(counts),
        "inactive_entries": len(rows),
        "emergency_third_qb_annotations": emergency,
        "team_entry_counts": dict(sorted(counts.items())),
        "zero_unparseable_entries": True,
        "zero_duplicate_team_sections": True,
        "zero_duplicate_players_within_team": True,
        "player_level_parser_qualified": False,
        "player_identity_to_gsis_qualified": False,
        "availability_probability_feature_authorized": False,
        "forecast_probability_effect_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    return ParsedInactiveArticle(rows=rows, audit=audit)


def qualify_against_contract(
    parsed: ParsedInactiveArticle,
    contract: dict[str, Any],
) -> dict[str, Any]:
    expected = contract["frozen_expected_source_shape"]
    artifact = contract["calibration_artifact"]
    gates = {
        "raw_sha256_exact": parsed.audit["raw_html_sha256"] == artifact["raw_html_sha256"],
        "team_section_count_exact": parsed.audit["team_sections"] == expected["team_sections"],
        "inactive_entry_count_exact": parsed.audit["inactive_entries"] == expected["inactive_entries"],
        "emergency_annotation_count_exact": (
            parsed.audit["emergency_third_qb_annotations"]
            == expected["emergency_third_qb_annotations"]
        ),
        "all_team_entry_counts_exact": parsed.audit["team_entry_counts"]
        == dict(sorted(expected["team_entry_counts"].items())),
        "zero_unparseable_entries": bool(parsed.audit["zero_unparseable_entries"]),
        "zero_duplicate_team_sections": bool(parsed.audit["zero_duplicate_team_sections"]),
        "zero_duplicate_players_within_team": bool(
            parsed.audit["zero_duplicate_players_within_team"]
        ),
    }

    observed_pairs = {
        (str(row["team"]), str(row["player_name_rendered"])) for row in parsed.rows
    }
    observed_emergency = {
        (str(row["team"]), str(row["player_name_rendered"]))
        for row in parsed.rows
        if row["emergency_third_qb"]
    }
    expected_pairs = {tuple(pair) for pair in expected["sentinel_player_team_pairs"]}
    expected_emergency = {tuple(pair) for pair in expected["sentinel_emergency_third_qbs"]}
    gates["all_sentinel_player_team_pairs_present"] = expected_pairs.issubset(observed_pairs)
    gates["all_sentinel_emergency_qbs_present"] = expected_emergency.issubset(observed_emergency)

    passed = all(gates.values())
    return {
        "contract_id": contract["contract_id"],
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if passed else "FAIL",
        "qualification_passed": passed,
        "gates": gates,
        "observed": {
            "raw_html_sha256": parsed.audit["raw_html_sha256"],
            "team_sections": parsed.audit["team_sections"],
            "inactive_entries": parsed.audit["inactive_entries"],
            "emergency_third_qb_annotations": parsed.audit[
                "emergency_third_qb_annotations"
            ],
            "team_entry_counts": parsed.audit["team_entry_counts"],
        },
        "authority": {
            "player_level_parser_qualified": passed,
            "player_identity_to_gsis_qualified": False,
            "availability_probability_feature_authorized": False,
            "player_value_join_authorized": False,
            "forecast_probability_effect_authorized": False,
            "production_authorized": False,
        },
        "completed_2026_outcomes_used": 0,
    }


def receipt_json(receipt: dict[str, Any]) -> str:
    return json.dumps(receipt, indent=2, sort_keys=True) + "\n"
