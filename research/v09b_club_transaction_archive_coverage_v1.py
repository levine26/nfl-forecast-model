from __future__ import annotations

"""Coverage-only audit for first-party club year-scoped transaction archives.

This module never interprets transaction text as roster state and never infers game-day
membership. It only asks whether each frozen 2017-2021 franchise-season exposes a qualifying
first-party `/team/transactions/{season}` page under the preregistered semantics.
"""

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests

CONTRACT_ID = "V09B-CLUB-TRANSACTION-ARCHIVE-COVERAGE-V1"
SEASONS = (2017, 2018, 2019, 2020, 2021)

TEAM_DOMAINS: dict[str, tuple[str, ...]] = {
    "ARI": ("azcardinals.com",),
    "ATL": ("atlantafalcons.com",),
    "BAL": ("baltimoreravens.com",),
    "BUF": ("buffalobills.com",),
    "CAR": ("panthers.com",),
    "CHI": ("chicagobears.com",),
    "CIN": ("bengals.com",),
    "CLE": ("clevelandbrowns.com",),
    "DAL": ("dallascowboys.com",),
    "DEN": ("denverbroncos.com",),
    "DET": ("detroitlions.com",),
    "GB": ("packers.com",),
    "HOU": ("houstontexans.com",),
    "IND": ("colts.com",),
    "JAX": ("jaguars.com",),
    "KC": ("chiefs.com",),
    "OAK": ("raiders.com",),
    "LV": ("raiders.com",),
    "LAC": ("chargers.com",),
    "LA": ("therams.com",),
    "MIA": ("miamidolphins.com",),
    "MIN": ("vikings.com",),
    "NE": ("patriots.com",),
    "NO": ("neworleanssaints.com",),
    "NYG": ("giants.com",),
    "NYJ": ("newyorkjets.com",),
    "PHI": ("philadelphiaeagles.com",),
    "PIT": ("steelers.com",),
    "SEA": ("seahawks.com",),
    "SF": ("49ers.com",),
    "TB": ("buccaneers.com",),
    "TEN": ("tennesseetitans.com",),
    "WAS": ("commanders.com", "washingtonfootball.com", "redskins.com"),
}

NON_RAIDERS = (
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET",
    "GB", "HOU", "IND", "JAX", "KC", "LAC", "LA", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
)

MONTHS = (
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
    "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
)
DATE_RE = re.compile(r"(?<!\d)(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])(?!\d)")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def teams_for_season(season: int) -> tuple[str, ...]:
    if season not in SEASONS:
        raise ValueError(f"unsupported season: {season}")
    raiders = "OAK" if season <= 2019 else "LV"
    teams = tuple(sorted((*NON_RAIDERS, raiders)))
    if len(teams) != 32 or len(set(teams)) != 32:
        raise RuntimeError("season team universe must contain exactly 32 unique clubs")
    return teams


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def visible_text(raw_html: str) -> str:
    without_script = SCRIPT_STYLE_RE.sub(" ", raw_html)
    without_tags = TAG_RE.sub(" ", without_script)
    return SPACE_RE.sub(" ", html.unescape(without_tags)).strip()


def host_allowed(host: str, domains: Iterable[str]) -> bool:
    host = host.lower().split(":", 1)[0]
    for domain in domains:
        d = domain.lower()
        if host == d or host == f"www.{d}":
            return True
    return False


def expected_path(season: int) -> str:
    return f"/team/transactions/{season}"


def evaluate_response(*, season: int, domains: tuple[str, ...], response: requests.Response) -> dict[str, Any]:
    raw = response.content
    raw_text = raw.decode(response.encoding or "utf-8", errors="replace")
    text = visible_text(raw_text)
    upper = text.upper()
    parsed = urlparse(str(response.url))
    final_path = parsed.path.rstrip("/")
    wanted_path = expected_path(season)
    dates = DATE_RE.findall(text)
    month_hits = sorted({month for month in MONTHS if month in upper})
    semantics = {
        "http_status_pass": int(response.status_code) < 400,
        "final_host_pass": host_allowed(parsed.netloc, domains),
        "final_path_pass": final_path == wanted_path,
        "transactions_marker_pass": "TRANSACTIONS" in upper,
        "month_heading_pass": bool(month_hits),
        "transaction_date_pass": bool(dates),
        "requested_season_signal_pass": str(season) in raw_text,
    }
    qualifying = all(semantics.values())
    return {
        "http_status": int(response.status_code),
        "final_url": str(response.url),
        "final_host": parsed.netloc,
        "final_path": final_path,
        "raw_bytes": len(raw),
        "raw_sha256": sha256_bytes(raw),
        "observed_transaction_date_count": len(dates),
        "observed_month_headings": month_hits,
        "semantics": semantics,
        "qualifying_page": qualifying,
    }


def candidate_urls(team: str, season: int) -> list[str]:
    return [f"https://www.{domain}{expected_path(season)}" for domain in TEAM_DOMAINS[team]]


def audit_team_season(
    *,
    team: str,
    season: int,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    domains = TEAM_DOMAINS[team]
    client = session or requests.Session()
    attempts: list[dict[str, Any]] = []
    qualifying: dict[str, Any] | None = None
    for url in candidate_urls(team, season):
        attempt: dict[str, Any] = {"requested_url": url}
        try:
            response = client.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={
                    "User-Agent": "LevLine-V09B-club-transaction-archive-coverage/1.0",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            attempt.update(evaluate_response(season=season, domains=domains, response=response))
        except Exception as exc:
            attempt.update({
                "error": f"{type(exc).__name__}: {exc}",
                "qualifying_page": False,
            })
        attempts.append(attempt)
        if attempt.get("qualifying_page") is True:
            qualifying = attempt
            break
    return {
        "season": season,
        "team": team,
        "candidate_attempts": attempts,
        "candidate_attempt_count": len(attempts),
        "qualifying_archive_found": qualifying is not None,
        "qualifying_archive": qualifying,
    }


def audit_season(season: int, *, timeout: float = 30.0) -> dict[str, Any]:
    teams = teams_for_season(season)
    session = requests.Session()
    rows = [audit_team_season(team=team, season=season, timeout=timeout, session=session) for team in teams]
    successes = [row for row in rows if row["qualifying_archive_found"]]
    missing = [row for row in rows if not row["qualifying_archive_found"]]
    http_statuses: Counter[str] = Counter()
    errors = 0
    attempts = 0
    for row in rows:
        for attempt in row["candidate_attempts"]:
            attempts += 1
            if "http_status" in attempt:
                http_statuses[str(attempt["http_status"])] += 1
            if attempt.get("error"):
                errors += 1
    return {
        "diagnostic_version": 1,
        "contract_id": CONTRACT_ID,
        "season": season,
        "team_season_pairs_expected": 32,
        "team_season_pairs_reported": len(rows),
        "team_season_pairs_with_qualifying_archive": len(successes),
        "team_season_pairs_missing": len(missing),
        "coverage_fraction": len(successes) / 32.0,
        "candidate_attempt_count": attempts,
        "http_status_distribution": dict(sorted(http_statuses.items())),
        "network_or_transport_errors": errors,
        "rows": rows,
        "accounting_integrity_pass": len(rows) == 32 and len(successes) + len(missing) == 32,
        "diagnostic_has_source_coverage_qualification_authority": False,
        "diagnostic_has_chronology_authority": False,
        "diagnostic_has_membership_authority": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "weekly_roster_membership_used": False,
        "weekly_roster_status_used": False,
        "postgame_participation_used_as_training_authority": False,
        "absence_from_inactive_used_as_positive": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }


def aggregate(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    by_season = {int(row["season"]): row for row in results}
    if set(by_season) != set(SEASONS):
        raise RuntimeError("aggregate requires exactly all five frozen seasons")
    total_reported = sum(int(row["team_season_pairs_reported"]) for row in by_season.values())
    total_found = sum(int(row["team_season_pairs_with_qualifying_archive"]) for row in by_season.values())
    total_missing = sum(int(row["team_season_pairs_missing"]) for row in by_season.values())
    attempts = sum(int(row["candidate_attempt_count"]) for row in by_season.values())
    errors = sum(int(row["network_or_transport_errors"]) for row in by_season.values())
    per_team: dict[str, dict[str, int]] = {}
    for season, result in sorted(by_season.items()):
        for row in result["rows"]:
            team = str(row["team"])
            franchise = "RAIDERS" if team in {"OAK", "LV"} else team
            stat = per_team.setdefault(franchise, {"reported": 0, "found": 0})
            stat["reported"] += 1
            stat["found"] += int(bool(row["qualifying_archive_found"]))
    for stat in per_team.values():
        stat["coverage_fraction"] = stat["found"] / stat["reported"] if stat["reported"] else 0.0
    return {
        "diagnostic_version": 1,
        "contract_id": CONTRACT_ID,
        "team_season_pairs_expected": 160,
        "team_season_pairs_reported": total_reported,
        "team_season_pairs_with_qualifying_archive": total_found,
        "team_season_pairs_missing": total_missing,
        "coverage_fraction": total_found / 160.0,
        "candidate_attempt_count": attempts,
        "network_or_transport_errors": errors,
        "per_season": {
            str(season): {
                "reported": int(result["team_season_pairs_reported"]),
                "found": int(result["team_season_pairs_with_qualifying_archive"]),
                "missing": int(result["team_season_pairs_missing"]),
                "coverage_fraction": float(result["coverage_fraction"]),
            }
            for season, result in sorted(by_season.items())
        },
        "per_team": dict(sorted(per_team.items())),
        "accounting_integrity_pass": total_reported == 160 and total_found + total_missing == 160,
        "coverage_is_descriptive_not_qualification_gate": True,
        "transaction_state_machine_defined": False,
        "same_day_transaction_order_resolved": False,
        "kickoff_relative_chronology_qualified": False,
        "absence_of_transaction_used_as_active_evidence": False,
        "diagnostic_has_source_coverage_qualification_authority": False,
        "diagnostic_has_chronology_authority": False,
        "diagnostic_has_membership_authority": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, choices=SEASONS)
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--inputs", nargs="*", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.aggregate:
        if args.season is not None or len(args.inputs) != 5:
            raise SystemExit("aggregate mode requires exactly five --inputs and no --season")
        result = aggregate(_load_json(path) for path in args.inputs)
    else:
        if args.season is None or args.inputs:
            raise SystemExit("season mode requires --season and no --inputs")
        result = audit_season(args.season, timeout=args.timeout)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2, sort_keys=True))
    if result.get("accounting_integrity_pass") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
