from __future__ import annotations

"""Research-only raw archive for official NFL inactive-report article surfaces.

NFL.com's generic /inactives/ landing page can lag the individual official news articles
that contain the actual game-day inactive lists. This collector therefore preserves the
NFL News index and every recent NFL-hosted news link whose anchor text or URL contains
"inactive" while a game is in the preregistered T-100..T-20 collection window.

This module deliberately does not parse player identities and is not authorized as a
probability feature. Its purpose is source preservation so a later, separately qualified
parser can be audited against the exact bytes available before kickoff.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests

ARCHIVE_ID = "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1"
SCHEMA_VERSION = 1
NEWS_INDEX_URL = "https://www.nfl.com/news/"
MANIFEST_NAME = "observations.jsonl"
RAW_DIR = "raw"
MAX_ARTICLE_URLS_PER_CAPTURE = 20


def _iso_utc(value: datetime | str | None = None) -> str:
    if value is None:
        dt = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_gzip_deterministic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(data)


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"inactive article archive has invalid JSON on line {line_number}") from exc
        if row.get("archive_id") != ARCHIVE_ID:
            raise ValueError("inactive article archive contains foreign archive_id")
        rows.append(row)
    return rows


def _append_manifest(path: Path, row: dict[str, Any]) -> None:
    existing = _load_manifest(path)
    identity = str(row["captured_at_utc"])
    if any(str(item.get("captured_at_utc")) == identity for item in existing):
        raise ValueError(f"duplicate inactive article capture identity: {identity}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def discover_inactive_article_urls(html: str, *, limit: int = MAX_ARTICLE_URLS_PER_CAPTURE) -> list[str]:
    """Return unique same-origin NFL news URLs that visibly identify inactive content."""
    soup = BeautifulSoup(str(html or ""), "html.parser")
    discovered: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        text = " ".join(anchor.get_text(" ", strip=True).split())
        signal = f"{text} {href}".casefold()
        if "inactiv" not in signal:
            continue
        absolute = urljoin(NEWS_INDEX_URL, href)
        parsed = urlparse(absolute)
        if parsed.scheme != "https" or parsed.netloc.casefold() not in {"www.nfl.com", "nfl.com"}:
            continue
        if not parsed.path.startswith("/news/"):
            continue
        canonical = f"https://www.nfl.com{parsed.path}"
        if canonical in seen:
            continue
        seen.add(canonical)
        discovered.append(canonical)
        if len(discovered) >= int(limit):
            break
    return discovered


def _raw_record(
    *,
    root: Path,
    source_kind: str,
    url: str,
    response: Any,
) -> dict[str, Any]:
    status = int(getattr(response, "status_code", 200))
    content = response.content if isinstance(response.content, bytes) else bytes(response.content)
    sha = _sha256(content)
    path = root / RAW_DIR / f"{sha}.html.gz"
    created = not path.exists()
    _write_gzip_deterministic(path, content)
    return {
        "source_kind": source_kind,
        "url": url,
        "http_status": status,
        "raw_body_sha256": sha,
        "raw_object_relpath": str(path.relative_to(root)),
        "raw_object_created": created,
        "bytes": len(content),
    }


def _get(session: Any, url: str, timeout_seconds: int) -> Any:
    return session.get(
        url,
        timeout=timeout_seconds,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; nfl-forecast-model/1.0; +https://github.com/levine26/nfl-forecast-model)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )


@dataclass(frozen=True)
class CaptureResult:
    observation: dict[str, Any]
    sources_captured: int


def capture_inactive_articles(
    *,
    output_dir: str | Path,
    due_games: list[dict[str, Any]],
    captured_at: datetime | str | None = None,
    session=requests,
    timeout_seconds: int = 25,
) -> CaptureResult:
    root = Path(output_dir)
    captured = _iso_utc(captured_at)
    sources: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    article_urls: list[str] = []

    try:
        response = _get(session, NEWS_INDEX_URL, timeout_seconds)
        news_record = _raw_record(
            root=root,
            source_kind="nfl_news_index",
            url=NEWS_INDEX_URL,
            response=response,
        )
        sources.append(news_record)
        if int(news_record["http_status"]) < 400:
            article_urls = discover_inactive_article_urls(response.text)
        else:
            errors.append({"url": NEWS_INDEX_URL, "error": f"HTTP {news_record['http_status']}"})
    except Exception as exc:
        errors.append({"url": NEWS_INDEX_URL, "error": str(exc)[:500]})

    for url in article_urls:
        try:
            response = _get(session, url, timeout_seconds)
            record = _raw_record(
                root=root,
                source_kind="nfl_inactives_news_article",
                url=url,
                response=response,
            )
            sources.append(record)
            if int(record["http_status"]) >= 400:
                errors.append({"url": url, "error": f"HTTP {record['http_status']}"})
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)[:500]})

    successful = [source for source in sources if int(source.get("http_status", 999)) < 400]
    observation = {
        "schema_version": SCHEMA_VERSION,
        "archive_id": ARCHIVE_ID,
        "captured_at_utc": captured,
        "due_games": due_games,
        "status": "captured_raw_sources" if successful else "failed",
        "news_index_url": NEWS_INDEX_URL,
        "discovered_inactive_article_urls": article_urls,
        "sources": sources,
        "errors": errors,
        "player_level_parser_qualified": False,
        "player_level_probability_feature_authorized": False,
        "probability_feature_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
        "research_only": True,
    }
    _append_manifest(root / MANIFEST_NAME, observation)
    return CaptureResult(observation=observation, sources_captured=len(successful))


def verify_archive(output_dir: str | Path) -> dict[str, Any]:
    root = Path(output_dir)
    rows = _load_manifest(root / MANIFEST_NAME)
    failures: list[str] = []
    seen_capture_times: set[str] = set()
    unique_raw: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        captured = str(row.get("captured_at_utc") or "")
        if captured in seen_capture_times:
            failures.append(f"duplicate captured_at_utc at row {row_number}: {captured}")
        seen_capture_times.add(captured)
        for gate in (
            "player_level_parser_qualified",
            "player_level_probability_feature_authorized",
            "probability_feature_authorized",
            "production_authorized",
        ):
            if row.get(gate) is not False:
                failures.append(f"row {row_number} violates {gate} firewall")
        if int(row.get("completed_2026_outcomes_used", -1)) != 0:
            failures.append(f"row {row_number} consumes completed 2026 outcomes")
        for source_number, source in enumerate(row.get("sources") or [], start=1):
            relpath = source.get("raw_object_relpath")
            sha = str(source.get("raw_body_sha256") or "")
            if not relpath or len(sha) != 64:
                failures.append(f"row {row_number} source {source_number} lacks raw identity")
                continue
            path = root / str(relpath)
            if not path.exists():
                failures.append(f"row {row_number} source {source_number} raw object missing")
                continue
            try:
                with gzip.open(path, "rb") as handle:
                    raw = handle.read()
            except Exception as exc:
                failures.append(f"row {row_number} source {source_number} unreadable: {exc}")
                continue
            if _sha256(raw) != sha:
                failures.append(f"row {row_number} source {source_number} SHA mismatch")
            else:
                unique_raw.add(sha)
    return {
        "archive_id": ARCHIVE_ID,
        "observations": len(rows),
        "unique_raw_objects": len(unique_raw),
        "integrity_ok": not failures,
        "failures": failures,
        "player_level_parser_qualified": False,
        "probability_feature_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
