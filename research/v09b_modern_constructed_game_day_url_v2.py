from __future__ import annotations

"""Constructed historical club game-day URL diagnostic over the frozen 2017-2021 universe."""

import argparse
import hashlib
import itertools
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-MODERN-CONSTRUCTED-GAME-DAY-URL-DIAGNOSTIC-V2"
STATIC_CLUB_HOST = "static.clubs.nfl.com"


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_game_id(game_id: str) -> tuple[int, int, str, str]:
    m = re.fullmatch(r"(20\d{2})_(\d{2})_([A-Z0-9]+)_([A-Z0-9]+)", str(game_id))
    if not m:
        raise ValueError(f"unexpected canonical game id: {game_id}")
    season, week, away, home = m.groups()
    return int(season), int(week), away, home


def read_snapshot(path: Path, contract: dict[str, Any]) -> list[str]:
    if sha256_file(path) != str(contract["canonical_snapshot"]["sha256"]):
        raise ValueError("canonical locator snapshot SHA mismatch")
    rows = []
    seen = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise ValueError(f"snapshot line {line_no} does not have two fields")
        game_id = parts[0].strip()
        parse_game_id(game_id)
        if game_id in seen:
            raise ValueError(f"duplicate canonical game id: {game_id}")
        seen.add(game_id)
        rows.append(game_id)
    if len(rows) != int(contract["canonical_snapshot"]["rows"]):
        raise ValueError("canonical locator snapshot row count mismatch")
    return rows


def team_hosts(domains: list[str]) -> set[str]:
    values = set()
    for domain in domains:
        d = str(domain).lower().removeprefix("www.")
        values.add(d)
        values.add("www." + d)
    return values


def canonical_https(url: str) -> str:
    p = urlparse(str(url))
    return urlunparse(("https", (p.hostname or "").lower(), p.path or "/", "", "", ""))


def page_signals_pass(text: str, *, week: int, away: str, home: str, signals: dict[str, list[str]]) -> tuple[bool, dict[str, bool]]:
    n = norm(text)
    week_ok = bool(re.search(rf"\bWEEK\s+{int(week)}\b", n))
    away_ok = any(norm(s) in n for s in signals[away])
    home_ok = any(norm(s) in n for s in signals[home])
    return week_ok and away_ok and home_ok, {"week": week_ok, "away": away_ok, "home": home_ok}


def classify_media(text: str, classes: dict[str, list[str]]) -> list[str]:
    n = norm(text)
    return [key for key, markers in classes.items() if any(norm(m) in n for m in markers)]


def extract_media_links(html: str, *, page_url: str, allowed_team_hosts: set[str], classes: dict[str, list[str]], limit: int) -> dict[str, list[dict[str, str]]]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    out = {key: [] for key in classes}
    seen = {key: set() for key in classes}
    for a in soup.find_all("a", href=True):
        label = " ".join(a.get_text(" ", strip=True).split())
        found_classes = classify_media(label, classes)
        if not found_classes:
            continue
        absolute = urljoin(page_url, str(a.get("href") or "").strip())
        p = urlparse(absolute)
        host = (p.hostname or "").lower()
        if p.scheme.lower() != "https" or (host != STATIC_CLUB_HOST and host not in allowed_team_hosts):
            continue
        u = canonical_https(absolute)
        for key in found_classes:
            ident = (label, u)
            if ident in seen[key] or len(out[key]) >= limit:
                continue
            seen[key].add(ident)
            out[key].append({"text": label[:500], "url": u, "host": host})
    return out


def candidate_urls(*, team: str, season: int, week: int, away: str, home: str, contract: dict[str, Any]) -> list[str]:
    template = str(contract["cms_grammar"]["url_template"])
    urls = []
    for domain, stage, away_slug, home_slug in itertools.product(
        contract["team_domains"][team],
        contract["cms_grammar"]["stage_variants_in_frozen_order"],
        contract["team_slug_variants"][away],
        contract["team_slug_variants"][home],
    ):
        urls.append(
            template.format(
                domain=domain,
                season=int(season),
                stage=str(stage).format(week=int(week)),
                away_slug=away_slug,
                home_slug=home_slug,
            )
        )
    return list(dict.fromkeys(urls))


def _get(url: str, timeout: float) -> Any:
    return requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-constructed-gameday/2.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )


def inspect_partition(task: dict[str, Any], contract: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    team = task["team"]
    allowed_hosts = team_hosts(contract["team_domains"][team])
    attempts = []
    qualifying = None
    for url in candidate_urls(team=team, season=task["season"], week=task["week"], away=task["away"], home=task["home"], contract=contract):
        attempt: dict[str, Any] = {
            "requested_url": url,
            "http_status": None,
            "final_url": None,
            "final_host_allowed": False,
            "page_signal_pass": False,
            "page_signals": {"week": False, "away": False, "home": False},
            "error": None,
        }
        try:
            response = _get(url, timeout)
            attempt["http_status"] = int(response.status_code)
            attempt["final_url"] = str(response.url)
            p = urlparse(str(response.url))
            attempt["final_host_allowed"] = p.scheme.lower() == "https" and (p.hostname or "").lower() in allowed_hosts
            if not attempt["final_host_allowed"]:
                attempt["error"] = f"final redirect escaped team allowlist: {(p.hostname or '').lower()}"
            elif response.status_code >= 400:
                attempt["error"] = f"HTTP {response.status_code}"
            else:
                visible = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
                passed, signals = page_signals_pass(
                    visible,
                    week=task["week"], away=task["away"], home=task["home"], signals=contract["team_visible_signals"]
                )
                attempt["page_signal_pass"] = passed
                attempt["page_signals"] = signals
                if not passed:
                    attempt["error"] = "HTTP page did not prove frozen week+matchup signals"
                else:
                    links = extract_media_links(
                        response.text,
                        page_url=str(response.url),
                        allowed_team_hosts=allowed_hosts,
                        classes=contract["media_classes"],
                        limit=int(contract["required_accounting"]["media_links_bounded_per_class_per_page"]),
                    )
                    qualifying = {
                        "requested_url": url,
                        "final_url": str(response.url),
                        "http_status": int(response.status_code),
                        "media_links": links,
                        "media_class_present": {k: bool(v) for k, v in links.items()},
                    }
        except Exception as exc:
            attempt["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        attempts.append(attempt)
        if qualifying is not None:
            break
    return {
        **task,
        "candidate_attempt_count": len(attempts),
        "candidate_attempts": attempts,
        "constructed_page_discovered": qualifying is not None,
        "qualifying_page": qualifying,
    }


def audit_season(contract_path: Path, snapshot_path: Path, *, season: int, timeout: float, workers: int) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    game_ids = read_snapshot(snapshot_path, contract)
    selected = [g for g in game_ids if parse_game_id(g)[0] == int(season)]
    expected_games = int(contract["expected_games_by_season"][str(season)])
    if len(selected) != expected_games:
        raise ValueError(f"season {season} canonical game count mismatch: {len(selected)} != {expected_games}")
    tasks = []
    for game_id in selected:
        s, week, away, home = parse_game_id(game_id)
        for team, side in ((away, "away"), (home, "home")):
            if team not in contract["team_domains"] or team not in contract["team_slug_variants"]:
                raise ValueError(f"missing frozen team mapping for {team}")
            tasks.append({"game_id": game_id, "season": s, "week": week, "away": away, "home": home, "team": team, "side": side})
    expected_partitions = int(contract["expected_team_partitions_by_season"][str(season)])
    if len(tasks) != expected_partitions:
        raise ValueError("partition count mismatch")
    rows = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(inspect_partition, task, contract, timeout=timeout): task for task in tasks}
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda x: (x["game_id"], x["side"]))
    media_counts = {key: 0 for key in contract["media_classes"]}
    for row in rows:
        q = row["qualifying_page"]
        if q:
            for key, present in q["media_class_present"].items():
                media_counts[key] += int(bool(present))
    integrity = len(rows) == expected_partitions and len({(x["game_id"], x["team"], x["side"]) for x in rows}) == expected_partitions
    return {
        "diagnostic_version": 2,
        "contract_id": CONTRACT_ID,
        "season": int(season),
        "canonical_games": len(selected),
        "team_partitions_expected": expected_partitions,
        "team_partitions_reported": len(rows),
        "constructed_pages_discovered": sum(1 for x in rows if x["constructed_page_discovered"]),
        "constructed_pages_missing": sum(1 for x in rows if not x["constructed_page_discovered"]),
        "candidate_attempts_total": sum(int(x["candidate_attempt_count"]) for x in rows),
        "media_class_partition_counts": media_counts,
        "accounting_integrity_pass": integrity,
        "partitions": rows,
        "diagnostic_has_locator_qualification_authority": False,
        "diagnostic_has_membership_authority": False,
        "modern_roster_depth_locator_coverage_qualified": False,
        "source_chronology_qualified": False,
        "transaction_reconciliation_performed": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "third_party_authority_used": False,
        "weekly_roster_membership_used": False,
        "weekly_roster_status_used": False,
        "postgame_participation_used_as_training_authority": False,
        "absence_from_inactive_used_as_positive": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }


def main(argv: Iterable[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--workers", type=int, default=32)
    args = p.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.contract, args.snapshot, season=args.season, timeout=args.timeout, workers=args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "partitions"}, indent=2, sort_keys=True))
    if not result["accounting_integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
