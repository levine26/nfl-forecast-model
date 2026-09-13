from __future__ import annotations

"""Discover official game-day inactive articles from NFL club article sitemaps.

Research-only locator diagnostic. Recovered articles have no label or membership authority.
"""

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from research import v09b_modern_gamebook_locator_audit_v1 as locator_v1

CONTRACT_ID = "V09B-MODERN-INACTIVE-ARTICLE-SITEMAP-DISCOVERY-V1"
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(value: str) -> str:
    value = str(value or "").replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", value).strip().lower()


def _hosts(domains: list[str]) -> set[str]:
    out: set[str] = set()
    for domain in domains:
        d = str(domain).lower().removeprefix("www.")
        out.add(d)
        out.add("www." + d)
    return out


def _host_allowed(url: str, domains: list[str]) -> bool:
    p = urlparse(str(url))
    return p.scheme.lower() == "https" and (p.hostname or "").lower() in _hosts(domains)


def _parse_game_id(game_id: str) -> tuple[int, int, str, str]:
    m = re.fullmatch(r"(20\d{2})_(\d{2})_([A-Z0-9]+)_([A-Z0-9]+)", str(game_id))
    if not m:
        raise ValueError(f"unexpected canonical game id: {game_id}")
    season, week, away, home = m.groups()
    return int(season), int(week), away, home


def _read_snapshot(path: Path, contract: dict[str, Any]) -> set[str]:
    expected = contract["dependencies"]["canonical_locator_snapshot"]
    if _sha256(path) != str(expected["sha256"]):
        raise ValueError("canonical locator snapshot SHA mismatch")
    ids: set[str] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise ValueError(f"invalid locator snapshot row {line_no}")
        game_id = parts[0].strip()
        _parse_game_id(game_id)
        if game_id in ids:
            raise ValueError(f"duplicate canonical game id: {game_id}")
        ids.add(game_id)
    if len(ids) != int(expected["rows"]):
        raise ValueError("canonical locator snapshot row count mismatch")
    return ids


def _game_date(game: dict[str, Any]) -> str:
    raw = game.get("gameday")
    if raw is None:
        raise ValueError(f"canonical schedule missing gameday for {game.get('game_id')}")
    if isinstance(raw, date):
        value = raw.isoformat()
    else:
        value = str(raw)[:10]
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value):
        raise ValueError(f"unexpected gameday for {game.get('game_id')}: {raw!r}")
    return value


def _title_matches(title: str, markers: list[str]) -> bool:
    n = _norm(title)
    return any(_norm(marker) in n for marker in markers)


def extract_sitemap_entries(
    html: str,
    *,
    sitemap_url: str,
    domains: list[str],
) -> list[dict[str, str]]:
    """Extract dated first-party article entries from a rendered HTML sitemap."""
    soup = BeautifulSoup(str(html or ""), "html.parser")
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for anchor in soup.find_all("a", href=True):
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not title:
            continue
        context_parts: list[str] = []
        node = anchor
        for _ in range(4):
            node = getattr(node, "parent", None)
            if node is None:
                break
            context_parts.append(" ".join(node.get_text(" ", strip=True).split())[:2000])
            if any(DATE_RE.search(x) for x in context_parts):
                break
        context = " ".join(context_parts)
        match = DATE_RE.search(context)
        if not match:
            continue
        article_date = match.group(1)
        absolute = urljoin(sitemap_url, str(anchor.get("href") or "").strip())
        if not _host_allowed(absolute, domains):
            continue
        ident = (article_date, title, absolute)
        if ident in seen:
            continue
        seen.add(ident)
        rows.append({"date": article_date, "title": title, "url": absolute})
    rows.sort(key=lambda row: (row["date"], row["title"], row["url"]))
    return rows


def _get(url: str, *, timeout: float) -> requests.Response:
    return requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-inactive-sitemap/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


def _fetch_sitemap(task: tuple[str, int, int, str], *, timeout: float, contract: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    team, year, month, domain = task
    url = str(contract["sitemap_discovery"]["url_template"]).format(
        domain=domain,
        year=year,
        month_zero_padded=f"{month:02d}",
    )
    row: dict[str, Any] = {
        "team": team,
        "year": year,
        "month": month,
        "domain": domain,
        "requested_url": url,
        "final_url": None,
        "http_status": None,
        "final_host_allowed": False,
        "entries": [],
        "error": None,
    }
    try:
        response = _get(url, timeout=timeout)
        row["http_status"] = int(response.status_code)
        row["final_url"] = str(response.url)
        row["final_host_allowed"] = _host_allowed(str(response.url), prior["team_domains"][team])
        if not row["final_host_allowed"]:
            row["error"] = "final redirect escaped team domain allowlist"
        elif response.status_code >= 400:
            row["error"] = f"HTTP {response.status_code}"
        else:
            row["entries"] = extract_sitemap_entries(
                response.text,
                sitemap_url=str(response.url),
                domains=prior["team_domains"][team],
            )
        response.close()
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
    return row


def _inspect_article(url: str, *, team: str, opponent: str, timeout: float, prior: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "url": url,
        "final_url": None,
        "http_status": None,
        "final_host_allowed": False,
        "inactive_signal": False,
        "opponent_signal": False,
        "qualifying_article": False,
        "error": None,
    }
    try:
        response = _get(url, timeout=timeout)
        row["http_status"] = int(response.status_code)
        row["final_url"] = str(response.url)
        row["final_host_allowed"] = _host_allowed(str(response.url), prior["team_domains"][team])
        if not row["final_host_allowed"]:
            row["error"] = "final redirect escaped team domain allowlist"
        elif response.status_code >= 400:
            row["error"] = f"HTTP {response.status_code}"
        else:
            visible = _norm(BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True))
            row["inactive_signal"] = bool(re.search(r"\binactives?\b", visible))
            row["opponent_signal"] = any(_norm(s) in visible for s in prior["team_visible_signals"][opponent])
            row["qualifying_article"] = bool(row["inactive_signal"] and row["opponent_signal"])
        response.close()
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
    return row


def audit_season(
    contract_path: Path,
    snapshot_path: Path,
    prior_contract_path: Path,
    *,
    season: int,
    timeout: float,
    workers: int,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    prior = json.loads(prior_contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    prior_expected = contract["dependencies"]["team_domain_and_visible_signal_contract"]
    if prior.get("contract_id") != prior_expected["contract_id"]:
        raise ValueError("unexpected prior domain contract id")
    snapshot_ids = _read_snapshot(snapshot_path, contract)

    games = locator_v1._canonical_games(int(season))
    schedule_ids = {str(g["game_id"]) for g in games}
    expected_ids = {g for g in snapshot_ids if g.startswith(f"{season}_")}
    if schedule_ids != expected_ids:
        raise ValueError("canonical schedule game IDs do not exactly match frozen locator snapshot")
    expected_games = int(contract["scope"]["expected_games_by_season"][str(season)])
    if len(games) != expected_games:
        raise ValueError("canonical schedule season count mismatch")

    partitions: list[dict[str, Any]] = []
    sitemap_tasks: set[tuple[str, int, int, str]] = set()
    for game in games:
        game_id = str(game["game_id"])
        _, week, away, home = _parse_game_id(game_id)
        gameday = _game_date(game)
        year, month = map(int, gameday.split("-")[:2])
        for team, opponent, side in ((away, home, "away"), (home, away, "home")):
            if team not in prior["team_domains"] or opponent not in prior["team_visible_signals"]:
                raise ValueError(f"missing frozen team mapping for {team}/{opponent}")
            for domain in prior["team_domains"][team]:
                sitemap_tasks.add((team, year, month, domain))
            partitions.append({
                "season": int(season),
                "week": week,
                "game_id": game_id,
                "gameday": gameday,
                "team": team,
                "opponent": opponent,
                "side": side,
            })

    sitemap_rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(_fetch_sitemap, task, timeout=timeout, contract=contract, prior=prior): task
            for task in sorted(sitemap_tasks)
        }
        for future in as_completed(futures):
            sitemap_rows.append(future.result())
    sitemap_rows.sort(key=lambda x: (x["team"], x["year"], x["month"], x["domain"]))

    sitemap_index: dict[tuple[str, int, int], list[dict[str, str]]] = {}
    for row in sitemap_rows:
        key = (row["team"], int(row["year"]), int(row["month"]))
        sitemap_index.setdefault(key, [])
        sitemap_index[key].extend(row["entries"])
    for key in list(sitemap_index):
        unique = {(r["date"], r["title"], r["url"]): r for r in sitemap_index[key]}
        sitemap_index[key] = sorted(unique.values(), key=lambda r: (r["date"], r["title"], r["url"]))

    markers = list(contract["sitemap_discovery"]["title_taxonomy_case_insensitive_substrings"])
    candidate_specs: list[tuple[str, str, str]] = []
    for row in partitions:
        year, month = map(int, row["gameday"].split("-")[:2])
        entries = sitemap_index.get((row["team"], year, month), [])
        row["sitemap_entries_on_game_date"] = [e for e in entries if e["date"] == row["gameday"]]
        row["title_taxonomy_candidates"] = [
            e for e in row["sitemap_entries_on_game_date"] if _title_matches(e["title"], markers)
        ]
        for e in row["title_taxonomy_candidates"]:
            candidate_specs.append((e["url"], row["team"], row["opponent"]))

    article_results: dict[tuple[str, str, str], dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(_inspect_article, url, team=team, opponent=opponent, timeout=timeout, prior=prior): (url, team, opponent)
            for url, team, opponent in sorted(set(candidate_specs))
        }
        for future in as_completed(futures):
            article_results[futures[future]] = future.result()

    for row in partitions:
        checked = []
        for e in row["title_taxonomy_candidates"]:
            result = dict(article_results[(e["url"], row["team"], row["opponent"])])
            result["title"] = e["title"]
            result["sitemap_date"] = e["date"]
            checked.append(result)
        row["candidate_articles_checked"] = checked
        row["qualifying_candidates"] = [x for x in checked if x["qualifying_article"]]
        row["qualifying_candidate_count"] = len(row["qualifying_candidates"])
        row["inactive_article_locator_state"] = (
            "unique" if len(row["qualifying_candidates"]) == 1 else
            "missing" if len(row["qualifying_candidates"]) == 0 else
            "ambiguous"
        )

    partitions.sort(key=lambda x: (x["game_id"], x["side"]))
    expected_partitions = expected_games * 2
    integrity = len(partitions) == expected_partitions and len({(r["game_id"], r["team"]) for r in partitions}) == expected_partitions
    states = {state: sum(r["inactive_article_locator_state"] == state for r in partitions) for state in ("unique", "missing", "ambiguous")}
    sitemap_http_success = sum(r["error"] is None for r in sitemap_rows)

    return {
        "diagnostic_version": 1,
        "contract_id": CONTRACT_ID,
        "season": int(season),
        "canonical_games": len(games),
        "team_partitions_expected": expected_partitions,
        "team_partitions_reported": len(partitions),
        "unique_team_month_domain_sitemap_attempts": len(sitemap_rows),
        "sitemap_attempts_without_error": sitemap_http_success,
        "sitemap_attempts_with_error": len(sitemap_rows) - sitemap_http_success,
        "partition_locator_states": states,
        "unique_inactive_article_fraction_diagnostic_only": states["unique"] / len(partitions) if partitions else 0.0,
        "accounting_integrity_pass": integrity,
        "sitemap_attempts": sitemap_rows,
        "partitions": partitions,
        "diagnostic_has_locator_qualification_authority": False,
        "diagnostic_has_membership_authority": False,
        "player_inactive_labels_parsed": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
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
    p.add_argument("--prior-contract", type=Path, required=True)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=12.0)
    p.add_argument("--workers", type=int, default=24)
    args = p.parse_args(list(argv) if argv is not None else None)
    result = audit_season(
        args.contract,
        args.snapshot,
        args.prior_contract,
        season=args.season,
        timeout=args.timeout,
        workers=args.workers,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"partitions", "sitemap_attempts"}}, indent=2, sort_keys=True))
    if not result["accounting_integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
