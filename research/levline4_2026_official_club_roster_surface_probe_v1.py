from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

CONTRACT_PATH = Path("research/levline4_2026_official_club_roster_surface_probe_v1_contract.json")
DEFAULT_OUTPUT = Path("research_outputs/levline4_2026_official_club_roster_surface_probe_v1")
PROFILE_PATH_RE = re.compile(r"^/team/players-roster/[^/?#]+/?$")
USER_AGENT = "LevLine-Research/1.0 (+https://github.com/levine26/nfl-forecast-model)"


@dataclass(frozen=True)
class HttpResult:
    status_code: int
    url: str
    headers: dict[str, str]
    content: bytes


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_host(host: str) -> str:
    host = host.lower().strip().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def host_allowed(candidate_url: str, frozen_host: str) -> bool:
    parsed = urlparse(candidate_url)
    return parsed.scheme == "https" and canonical_host(parsed.hostname or "") == canonical_host(frozen_host)


def request_with_frozen_redirects(
    url: str,
    frozen_host: str,
    *,
    get: Callable[..., object] = requests.get,
    max_redirects: int = 5,
) -> HttpResult:
    current = url
    for hop in range(max_redirects + 1):
        if not host_allowed(current, frozen_host):
            raise RuntimeError(f"disallowed_request_host:{current}")
        response = get(
            current,
            allow_redirects=False,
            timeout=(10, 25),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
            },
        )
        status = int(response.status_code)
        headers = {str(k): str(v) for k, v in response.headers.items()}
        if status in {301, 302, 303, 307, 308}:
            if hop >= max_redirects:
                raise RuntimeError("redirect_limit_exceeded")
            location = headers.get("Location") or headers.get("location")
            if not location:
                raise RuntimeError("redirect_without_location")
            nxt = urljoin(current, location)
            if not host_allowed(nxt, frozen_host):
                raise RuntimeError(f"disallowed_redirect_host:{nxt}")
            current = nxt
            continue
        return HttpResult(
            status_code=status,
            url=str(response.url or current),
            headers=headers,
            content=bytes(response.content),
        )
    raise RuntimeError("unreachable_redirect_state")


def normalize_header(text: str) -> str:
    return " ".join(text.split()).strip()


def table_has_player_number_position(headers: list[str]) -> bool:
    lowered = {h.lower() for h in headers if h}
    has_player = any(h == "player" or "player" in h for h in lowered)
    has_number = any(h in {"#", "no", "no.", "number", "num"} or "number" in h for h in lowered)
    has_position = any(h in {"pos", "pos.", "position"} or "position" in h for h in lowered)
    return has_player and has_number and has_position


def diagnose_html(team: str, source_url: str, final_url: str, captured_at: str, raw: bytes) -> dict:
    soup = BeautifulSoup(raw, "lxml")
    raw_sha = sha256_bytes(raw)
    links: dict[str, dict] = {}
    link_hosts: Counter[str] = Counter()

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        absolute = urljoin(final_url, href)
        parsed = urlparse(absolute)
        if not PROFILE_PATH_RE.match(parsed.path):
            continue
        normalized = absolute.split("#", 1)[0].split("?", 1)[0]
        link_hosts[canonical_host(parsed.hostname or "")] += 1
        links.setdefault(
            normalized,
            {
                "team": team,
                "profile_url": normalized,
                "anchor_text": normalize_header(anchor.get_text(" ", strip=True)),
                "source_url": source_url,
                "final_url": final_url,
                "captured_at_utc": captured_at,
                "raw_html_sha256": raw_sha,
            },
        )

    header_vectors: list[list[str]] = []
    qualifying_tables = 0
    for table in soup.find_all("table"):
        headers = [normalize_header(th.get_text(" ", strip=True)) for th in table.find_all("th")]
        if headers:
            header_vectors.append(headers)
            if table_has_player_number_position(headers):
                qualifying_tables += 1

    return {
        "raw_html_sha256": raw_sha,
        "raw_html_bytes": len(raw),
        "unique_profile_url_count": len(links),
        "profile_links": [links[k] for k in sorted(links)],
        "profile_link_host_counts": dict(sorted(link_hosts.items())),
        "html_table_header_vectors": header_vectors,
        "tables_with_player_number_position_headers": qualifying_tables,
        "next_data_script_present": soup.find("script", id="__NEXT_DATA__") is not None,
        "json_ld_script_count": len(soup.find_all("script", attrs={"type": "application/ld+json"})),
        "surface_presence": bool(links),
    }


def capture_team(team: str, host: str, roster_path: str, *, get: Callable[..., object] = requests.get) -> tuple[dict, bytes, list[dict]]:
    source_url = f"https://{host}{roster_path}"
    captured_at = utc_now()
    result = request_with_frozen_redirects(source_url, host, get=get)
    if not host_allowed(result.url, host):
        raise RuntimeError(f"final_url_left_frozen_host:{result.url}")
    content_type = result.headers.get("Content-Type") or result.headers.get("content-type") or ""
    diagnostic = diagnose_html(team, source_url, result.url, captured_at, result.content)
    record = {
        "team": team,
        "host": host,
        "source_url": source_url,
        "final_url": result.url,
        "captured_at_utc": captured_at,
        "http_status": result.status_code,
        "http_success": 200 <= result.status_code < 300,
        "content_type": content_type,
        **{k: v for k, v in diagnostic.items() if k != "profile_links"},
    }
    return record, result.content, diagnostic["profile_links"]


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    contract = json.loads(path.read_text())
    assert contract["contract_id"] == "LEVLINE-4-2026-OFFICIAL-CLUB-ROSTER-SURFACE-PROBE-V1"
    assert contract["status"] == "PREREGISTERED_SOURCE_SURFACE_CAPTURE_AND_DIAGNOSTIC_ONLY"
    assert len(contract["source_discovery"]["clubs"]) == 32
    assert contract["projection_policy"]["roster_section_or_status_selected"] is False
    assert contract["authority"]["production_authorized"] is False
    return contract


def run_capture(output_dir: Path = DEFAULT_OUTPUT, *, get: Callable[..., object] = requests.get) -> dict:
    contract = load_contract()
    clubs: dict[str, str] = contract["source_discovery"]["clubs"]
    roster_path: str = contract["source_discovery"]["roster_path"]
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    teams: list[dict] = []
    profile_links: list[dict] = []
    errors: list[dict] = []

    for team, host in clubs.items():
        try:
            record, raw, links = capture_team(team, host, roster_path, get=get)
            (raw_dir / f"{team}.html").write_bytes(raw)
            teams.append(record)
            profile_links.extend(links)
        except Exception as exc:  # preserve negative evidence rather than silently dropping a club
            errors.append({"team": team, "host": host, "error_type": type(exc).__name__, "error": str(exc)})

    captured_teams = {r["team"] for r in teams}
    expected_teams = set(clubs)
    http_success_teams = {r["team"] for r in teams if r["http_success"]}
    surface_teams = {r["team"] for r in teams if r["surface_presence"]}
    capture_complete = captured_teams == expected_teams and http_success_teams == expected_teams and not errors
    surface_probe_complete = capture_complete and surface_teams == expected_teams

    (output_dir / "team_diagnostics.json").write_text(json.dumps(teams, indent=2, sort_keys=True) + "\n")
    with (output_dir / "profile_links.jsonl").open("w") as fh:
        for row in sorted(profile_links, key=lambda r: (r["team"], r["profile_url"])):
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    receipt = {
        "schema_version": "levline4-2026-official-club-roster-surface-probe-v1",
        "contract_id": contract["contract_id"],
        "status": "PASS" if surface_probe_complete else "FAIL",
        "capture_started_or_completed_at_utc": utc_now(),
        "expected_team_count": 32,
        "captured_team_count": len(captured_teams),
        "http_success_team_count": len(http_success_teams),
        "surface_presence_team_count": len(surface_teams),
        "profile_link_rows": len(profile_links),
        "capture_complete": capture_complete,
        "official_club_roster_surface_capture_qualified": surface_probe_complete,
        "errors": errors,
        "name_jersey_position_parser_qualified": False,
        "official_club_roster_identity_parser_qualified": False,
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
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_capture(args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
