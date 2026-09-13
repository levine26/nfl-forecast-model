from __future__ import annotations

"""Hardened execution wrapper for the 2017-2021 Game Book locator audit.

The V1 diagnostic showed that broad embedded-PDF discovery can surface unrelated documents
already present in NFL page payloads. V2 therefore applies a strict evidence precedence:
use an explicit Download Game Book anchor when present, and consult embedded first-party
Game Center PDF URLs only when the anchor surface is absent. It also verifies the final
redirect target of every NFL discovery/document request so a first-party requested URL
cannot silently terminate on a non-first-party host. All V1 coverage thresholds, schedule
fallback logic, and research-only governance remain unchanged.
"""

import argparse
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from research import v09b_modern_gamebook_locator_audit_v1 as v1


def extract_gamebook_evidence(html: str, base_url: str) -> tuple[list[str], str]:
    soup = BeautifulSoup(html, "html.parser")
    anchors: list[str] = []
    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.stripped_strings).lower()
        if "download game book" not in text:
            continue
        anchors.append(urljoin(base_url, str(anchor["href"]).strip()))
    anchors = v1._dedupe(anchors)
    if anchors:
        return anchors, "download_anchor"

    embedded = v1._embedded_first_party_pdf_links(html)
    if embedded:
        return embedded, "embedded_first_party_pdf"
    return [], "none"


def redirect_target_allowed(requested_url: str, final_url: str) -> bool:
    """Require redirects to remain inside the first-party host class requested.

    NFL Game Center / schedule requests may redirect between nfl.com and www.nfl.com.
    Static Game Book document requests must terminate on static.www.nfl.com. Unknown
    requested hosts fail closed rather than inheriting trust from the final response.
    """
    requested = urlparse(requested_url)
    final = urlparse(final_url)
    if final.scheme != "https":
        return False
    if requested.scheme != "https":
        return False
    if requested.hostname in v1.ALLOWED_GAME_CENTER_HOSTS:
        return final.hostname in v1.ALLOWED_GAME_CENTER_HOSTS
    if requested.hostname in v1.ALLOWED_DOCUMENT_HOSTS:
        return final.hostname in v1.ALLOWED_DOCUMENT_HOSTS
    return False


def audit_season(*args, **kwargs):
    original_evidence = v1.extract_gamebook_evidence
    original_request = v1._request

    def provenance_request(session, url: str, *, timeout: float, attempts: int):
        response = original_request(session, url, timeout=timeout, attempts=attempts)
        final_url = str(getattr(response, "url", url) or url)
        if not redirect_target_allowed(url, final_url):
            response.close()
            raise RuntimeError(
                "first-party request redirected outside authorized host class: "
                f"requested={url} final={final_url}"
            )
        return response

    v1.extract_gamebook_evidence = extract_gamebook_evidence
    v1._request = provenance_request
    try:
        return v1.audit_season(*args, **kwargs)
    finally:
        v1.extract_gamebook_evidence = original_evidence
        v1._request = original_request


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(v1.EXPECTED_GAMES))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(
        args.season,
        timeout=args.timeout,
        attempts=args.attempts,
        delay_seconds=args.delay_seconds,
    )
    v1.write_result(result, args.output)
    import json
    print(json.dumps({k: value for k, value in result.items() if k != "rows"}, indent=2, sort_keys=True))
    if result["all_gamebook_locators_qualified"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
