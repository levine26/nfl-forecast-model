from __future__ import annotations

"""Discovery-only probe for official NFL club player-profile source surfaces.

The sample is selected deterministically from the frozen V2 official-club roster
metadata artifact. This module records source structure and candidate identifier
signals only. It does not qualify an identifier parser or any player->GSIS bridge.
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from research import levline4_2026_official_club_roster_surface_probe_v1 as source_v1

CONTRACT_PATH = Path("research/levline4_2026_official_club_player_profile_surface_probe_v1_contract.json")
DEFAULT_OUTPUT = Path("research_outputs/levline4_2026_official_club_player_profile_surface_probe_v1")
GSIS_LIKE_RE = re.compile(r"00-[0-9]{7}")
ID_LIKE_ATTR_RE = re.compile(r"(^id$|(^|[-_:])(id|player|athlete|person|gsis|nfl)([-_:]|$))", re.I)


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    assert contract["contract_id"] == "LEVLINE-4-2026-OFFICIAL-CLUB-PLAYER-PROFILE-SURFACE-PROBE-V1"
    assert contract["status"] == "PREREGISTERED_SOURCE_SURFACE_CAPTURE_AND_DIAGNOSTIC_ONLY"
    assert contract["sample_selection"]["expected_team_count"] == 32
    assert contract["sample_selection"]["manual_player_selection_allowed"] is False
    assert contract["diagnostics_only"]["candidate_presence_is_not_identifier_qualification"] is True
    assert contract["authority_even_if_gate_passes"]["player_identity_to_gsis_qualified"] is False
    assert contract["authority_even_if_gate_passes"]["production_authorized"] is False
    return contract


def load_roster_metadata(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        for key in ("team", "visible_name", "profile_path", "final_url", "raw_html_sha256"):
            if key not in row:
                raise RuntimeError(f"missing_roster_metadata_field:{line_number}:{key}")
        rows.append(row)
    if not rows:
        raise RuntimeError("empty_roster_metadata")
    return rows


def select_profiles(rows: list[dict[str, Any]], expected_team_count: int = 32) -> list[dict[str, Any]]:
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        team = normalize_text(row.get("team"))
        profile_path = normalize_text(row.get("profile_path"))
        final_url = normalize_text(row.get("final_url"))
        if not team or not profile_path or not final_url:
            raise RuntimeError("invalid_roster_metadata_selection_row")
        by_team[team].append(row)
    if len(by_team) != expected_team_count:
        raise RuntimeError(f"unexpected_team_count:{len(by_team)}")

    selected: list[dict[str, Any]] = []
    for team in sorted(by_team):
        candidates = sorted(by_team[team], key=lambda r: (str(r["profile_path"]), str(r["visible_name"])))
        minimum_path = str(candidates[0]["profile_path"])
        minimum_rows = [r for r in candidates if str(r["profile_path"]) == minimum_path]
        if len(minimum_rows) != 1:
            raise RuntimeError(f"nonunique_minimum_profile_path:{team}:{minimum_path}:{len(minimum_rows)}")
        row = minimum_rows[0]
        host = urlparse(str(row["final_url"])).hostname or ""
        if not host:
            raise RuntimeError(f"missing_selected_host:{team}")
        profile_url = urljoin(str(row["final_url"]), str(row["profile_path"]))
        if not source_v1.host_allowed(profile_url, host):
            raise RuntimeError(f"selected_profile_left_frozen_host:{team}:{profile_url}")
        selected.append(
            {
                "team": team,
                "visible_name": normalize_text(row["visible_name"]),
                "profile_path": str(row["profile_path"]),
                "profile_url": profile_url,
                "host": host,
                "roster_page_final_url": str(row["final_url"]),
                "roster_page_raw_html_sha256": str(row["raw_html_sha256"]),
            }
        )
    return selected


def _bounded_append(store: dict[str, list[str]], key: str, value: str, limit: int) -> None:
    values = store.setdefault(key, [])
    if value not in values and len(values) < limit:
        values.append(value)


def diagnose_profile_html(raw_html: bytes, *, contract: dict[str, Any]) -> dict[str, Any]:
    text = raw_html.decode("utf-8", errors="replace")
    soup = BeautifulSoup(raw_html, "lxml")
    token_counts: dict[str, int] = {}
    for token in contract["diagnostics_only"]["literal_token_patterns"]:
        token_counts[token] = len(re.findall(re.escape(str(token)), text, flags=re.I))

    gsis_like_values = sorted(set(GSIS_LIKE_RE.findall(text)))
    sample_limit = int(contract["diagnostics_only"]["maximum_attribute_samples_per_name"])
    attr_counts: Counter[str] = Counter()
    attr_samples: dict[str, list[str]] = {}
    for tag in soup.find_all(True):
        for raw_name, raw_value in tag.attrs.items():
            name = str(raw_name)
            if not ID_LIKE_ATTR_RE.search(name):
                continue
            attr_counts[name] += 1
            if isinstance(raw_value, list):
                value = " ".join(str(x) for x in raw_value)
            else:
                value = str(raw_value)
            _bounded_append(attr_samples, name, normalize_text(value), sample_limit)

    script_ids = sorted({normalize_text(tag.get("id")) for tag in soup.find_all("script") if normalize_text(tag.get("id"))})
    script_types = sorted({normalize_text(tag.get("type")) for tag in soup.find_all("script") if normalize_text(tag.get("type"))})
    canonical_links = []
    for link in soup.find_all("link", href=True):
        rel = [str(x).lower() for x in (link.get("rel") or [])]
        if "canonical" in rel:
            canonical_links.append(str(link.get("href")))

    return {
        "raw_html_sha256": source_v1.sha256_bytes(raw_html),
        "raw_html_bytes": len(raw_html),
        "literal_token_counts": token_counts,
        "gsis_like_values": gsis_like_values,
        "gsis_like_value_count": len(gsis_like_values),
        "id_like_attribute_name_counts": dict(sorted(attr_counts.items())),
        "id_like_attribute_samples": {k: attr_samples[k] for k in sorted(attr_samples)},
        "script_ids": script_ids,
        "script_types": script_types,
        "json_ld_script_count": len(soup.find_all("script", attrs={"type": "application/ld+json"})),
        "next_data_script_present": soup.find("script", id="__NEXT_DATA__") is not None,
        "canonical_links": sorted(set(canonical_links)),
    }


def capture_profile(
    selected: dict[str, Any],
    *,
    contract: dict[str, Any],
    get: Callable[..., object] = requests.get,
) -> tuple[dict[str, Any], bytes]:
    captured_at = source_v1.utc_now()
    result = source_v1.request_with_frozen_redirects(
        str(selected["profile_url"]),
        str(selected["host"]),
        get=get,
    )
    if not source_v1.host_allowed(result.url, str(selected["host"])):
        raise RuntimeError(f"final_url_left_selected_host:{selected['team']}:{result.url}")
    diagnostic = diagnose_profile_html(result.content, contract=contract)
    return (
        {
            **selected,
            "captured_at_utc": captured_at,
            "final_url": result.url,
            "http_status": int(result.status_code),
            "http_success": 200 <= int(result.status_code) < 300,
            "content_type": result.headers.get("Content-Type") or result.headers.get("content-type") or "",
            **diagnostic,
        },
        result.content,
    )


def run_probe(
    roster_metadata_path: Path,
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    get: Callable[..., object] = requests.get,
) -> dict[str, Any]:
    contract = load_contract()
    rows = load_roster_metadata(roster_metadata_path)
    selected = select_profiles(rows, int(contract["sample_selection"]["expected_team_count"]))

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "selected_profiles.json").write_text(
        json.dumps(selected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    diagnostics: list[dict[str, Any]] = []
    source_errors: list[dict[str, Any]] = []
    for row in selected:
        team = str(row["team"])
        try:
            diagnostic, raw = capture_profile(row, contract=contract, get=get)
            (raw_dir / f"{team}.html").write_bytes(raw)
            diagnostics.append(diagnostic)
        except Exception as exc:
            source_errors.append(
                {
                    "team": team,
                    "profile_url": row["profile_url"],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    diagnostics.sort(key=lambda r: str(r["team"]))
    (output_dir / "team_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    expected_teams = {str(r["team"]) for r in selected}
    captured_teams = {str(r["team"]) for r in diagnostics}
    http_success_teams = {str(r["team"]) for r in diagnostics if r.get("http_success") is True}
    raw_file_teams = {p.stem for p in raw_dir.glob("*.html")}
    gate_pass = (
        len(expected_teams) == 32
        and captured_teams == expected_teams
        and http_success_teams == expected_teams
        and raw_file_teams == expected_teams
        and not source_errors
    )

    pages_with_gsis_like = sum(1 for r in diagnostics if int(r["gsis_like_value_count"]) > 0)
    token_page_counts = {
        token: sum(1 for r in diagnostics if int(r["literal_token_counts"].get(token, 0)) > 0)
        for token in contract["diagnostics_only"]["literal_token_patterns"]
    }
    candidate_attr_names = sorted(
        {
            name
            for r in diagnostics
            for name in r["id_like_attribute_name_counts"].keys()
        }
    )

    receipt = {
        "schema_version": "levline4-2026-official-club-player-profile-surface-probe-v1",
        "contract_id": contract["contract_id"],
        "status": "PASS" if gate_pass else "FAIL",
        "capture_completed_at_utc": source_v1.utc_now(),
        "dependency_workflow_run_id": contract["frozen_dependency"]["canonical_workflow_run_id"],
        "dependency_artifact_id": contract["frozen_dependency"]["canonical_artifact_id"],
        "expected_team_count": 32,
        "selected_profile_count": len(selected),
        "captured_team_count": len(captured_teams),
        "http_success_team_count": len(http_success_teams),
        "raw_file_team_count": len(raw_file_teams),
        "source_errors": source_errors,
        "pages_with_gsis_like_values": pages_with_gsis_like,
        "literal_token_page_counts": token_page_counts,
        "observed_id_like_attribute_names": candidate_attr_names,
        "official_club_player_profile_surface_capture_qualified": gate_pass,
        "official_stable_player_identifier_exposed_qualified": False,
        "official_identifier_parser_qualified": False,
        "official_identifier_to_gsis_bridge_qualified": False,
        "player_identity_to_gsis_qualified": False,
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified": False,
        "general_2026_player_identity_to_gsis_qualified": False,
        "game_day_membership_qualified": False,
        "availability_state_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "f_st_01_frozen_2026_unchanged": True,
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roster-metadata", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_probe(args.roster_metadata, args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
