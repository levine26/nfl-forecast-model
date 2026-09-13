from __future__ import annotations

"""Club-specific provenance audit for delegated NFL media hosts.

Only the relation between a frozen club-owned origin and a frozen delegated host is tested.
No provider-wide trust, historical locator coverage, roster membership, labels, or model
authority is created here.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-DELEGATED-MEDIA-PROVENANCE-V1"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _host(url: str) -> str:
    return (urlparse(str(url)).hostname or "").lower()


def _validate_https(url: str) -> None:
    if urlparse(str(url)).scheme.lower() != "https":
        raise ValueError(f"non-https URL: {url}")


def _text(html: str) -> str:
    return " ".join(BeautifulSoup(html, "html.parser").get_text(" ", strip=True).split())


def _delegated_links(html: str, base_url: str, delegated_host: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        url = urljoin(base_url, str(anchor.get("href") or ""))
        if _host(url) != delegated_host:
            continue
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


def _markers(text: str, required: list[str]) -> dict[str, bool]:
    folded = text.casefold()
    return {marker: marker.casefold() in folded for marker in required}


def fetch_origin(url: str, *, timeout: float) -> tuple[Any, list[dict[str, Any]]]:
    _validate_https(url)
    response = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-delegated-media-provenance/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    response.raise_for_status()
    chain = [
        {
            "status_code": int(item.status_code),
            "url": str(item.url),
            "location": str(item.headers.get("location", "")),
        }
        for item in response.history
    ]
    chain.append({"status_code": int(response.status_code), "url": str(response.url), "location": ""})
    return response, chain


def audit_candidate(item: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    origin = str(item["official_origin"])
    delegated = str(item["expected_delegated_host"]).lower()
    relation = str(item["relation"])
    response, chain = fetch_origin(origin, timeout=timeout)
    final_url = str(response.url)
    final_host = _host(final_url)
    raw = response.content
    html = raw.decode("utf-8", errors="replace")
    text = _text(html)
    marker_map = _markers(text, list(item["required_markers"]))
    links = _delegated_links(html, final_url, delegated)

    if relation == "redirect":
        relation_evidence = final_host == delegated and any(
            _host(step.get("url", "")) == delegated for step in chain
        )
        min_link_gate = True
    elif relation == "linked":
        minimum = int(item.get("minimum_delegated_links", 1))
        relation_evidence = len(links) >= minimum
        min_link_gate = len(links) >= minimum
    else:
        raise ValueError(f"unsupported relation: {relation}")

    qualified = bool(relation_evidence and all(marker_map.values()))
    return {
        "team": str(item["team"]),
        "official_origin": origin,
        "relation": relation,
        "expected_delegated_host": delegated,
        "redirect_chain": chain,
        "final_url": final_url,
        "final_host": final_host,
        "raw_bytes": len(raw),
        "raw_sha256": _sha(raw),
        "marker_presence": marker_map,
        "delegated_link_count": len(links),
        "delegated_link_examples": links[:30],
        "minimum_delegated_link_gate_pass": min_link_gate,
        "relation_evidence_pass": relation_evidence,
        "club_specific_delegation_provenance_qualified": qualified,
    }


def observe_only(item: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    origin = str(item["official_origin"])
    try:
        response, chain = fetch_origin(origin, timeout=timeout)
        raw = response.content
        return {
            "team": str(item["team"]),
            "official_origin": origin,
            "prior_observed_target": str(item["observed_prior_target"]),
            "success": True,
            "redirect_chain": chain,
            "final_url": str(response.url),
            "final_host": _host(str(response.url)),
            "raw_bytes": len(raw),
            "raw_sha256": _sha(raw),
            "bounded_text": _text(raw.decode("utf-8", errors="replace"))[:2000],
            "qualification_evaluated": False,
        }
    except Exception as exc:
        return {
            "team": str(item["team"]),
            "official_origin": origin,
            "prior_observed_target": str(item["observed_prior_target"]),
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
            "qualification_evaluated": False,
        }


def run(contract_path: Path, *, timeout: float) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for item in contract["qualification_candidates"]:
        try:
            candidates.append(audit_candidate(item, timeout=timeout))
        except Exception as exc:
            errors.append({"team": str(item.get("team")), "error": f"{type(exc).__name__}: {exc}"})
    observations = [observe_only(item, timeout=timeout) for item in contract["observation_only"]]
    qualified_clubs = sorted(
        row["team"] for row in candidates if row["club_specific_delegation_provenance_qualified"]
    )
    gate_pass = len(candidates) == 2 and not errors and qualified_clubs == ["CLE", "PHI"]
    return {
        "audit_version": 1,
        "contract_id": CONTRACT_ID,
        "candidate_count_expected": 2,
        "candidate_count_completed": len(candidates),
        "candidate_errors": errors,
        "candidates": candidates,
        "observation_only": observations,
        "qualified_clubs": qualified_clubs,
        "club_specific_delegation_provenance_gate_pass": gate_pass,
        "delegated_provider_globally_qualified": False,
        "historical_document_locator_coverage_qualified": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "weekly_roster_membership_used": False,
        "weekly_roster_status_used": False,
        "postgame_participation_used_as_training_authority": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run(args.contract, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"candidates", "observation_only"}}, indent=2, sort_keys=True))
    if result["club_specific_delegation_provenance_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
