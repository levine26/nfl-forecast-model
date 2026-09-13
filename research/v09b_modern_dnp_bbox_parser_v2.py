from __future__ import annotations

"""Coordinate-aware NFL Game Book DNP parser for the V09B diagnostic.

This module fixes a diagnostic parser defect discovered after the zero-authority V1
first run. It changes only PDF geometry parsing; it does not change the frozen source
contract, weekly-roster semantics, qualification authority, or any model gate.
"""

import gzip
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any
import xml.etree.ElementTree as ET

from research.v09b_modern_dnp_weekly_roster_diagnostic_v1 import (
    DnpToken,
    TARGET_SEASONS,
    normalize_jersey,
    normalize_team,
    read_archive_manifest,
    sha256_bytes,
)

PARSER_VERSION = "BBOX_HALF_COLUMN_V2"
DNP_RE = re.compile(r"\bDid\s+Not\s+Play\b", flags=re.IGNORECASE)
NOT_ACTIVE_RE = re.compile(r"\bNot\s+Active\b", flags=re.IGNORECASE)
STOP_RE = re.compile(
    r"\b(?:Field\s+Goals?|Scoring\s+Plays?|Officials|Lineups|Substitutions|"
    r"Game\s+Statistics|Coin\s+Toss)\b",
    flags=re.IGNORECASE,
)
TOKEN_RE = re.compile(
    r"(?<!\S)(?P<jersey>\d{1,2})\s+"
    r"(?P<name>(?:[A-Z][a-z]{0,3}\.)?[A-Z][A-Za-z'’.\-]+)"
)
POSITION_TOKENS = {
    "QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "OL", "T", "G",
    "DE", "DT", "DL", "NT", "LB", "ILB", "OLB", "MLB", "WLB", "SLB", "CB", "DB",
    "S", "SS", "FS", "LCB", "RCB", "K", "P", "LS",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def extract_pdf_bbox_pages(raw_pdf: bytes) -> list[dict[str, Any]]:
    """Return physical PDF lines with word coordinates from Poppler bbox-layout."""
    with tempfile.TemporaryDirectory(prefix="v09b-dnp-bbox-") as tmp:
        pdf = Path(tmp) / "gamebook.pdf"
        html = Path(tmp) / "gamebook.html"
        pdf.write_bytes(raw_pdf)
        proc = subprocess.run(
            ["pdftotext", "-bbox-layout", str(pdf), str(html)],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0 or not html.exists():
            raise RuntimeError(f"pdftotext -bbox-layout failed: {proc.stderr.strip()}")
        try:
            root = ET.parse(html).getroot()
        except ET.ParseError as exc:
            raise RuntimeError(f"could not parse pdftotext bbox XHTML: {exc}") from exc

    pages: list[dict[str, Any]] = []
    page_number = 0
    for page_el in root.iter():
        if _local_name(page_el.tag) != "page":
            continue
        page_number += 1
        width = float(page_el.attrib.get("width", "0") or 0)
        height = float(page_el.attrib.get("height", "0") or 0)
        if width <= 0 or height <= 0:
            raise ValueError(f"invalid bbox page dimensions on page {page_number}")
        lines: list[dict[str, Any]] = []
        for line_el in page_el.iter():
            if _local_name(line_el.tag) != "line":
                continue
            words: list[dict[str, Any]] = []
            for word_el in line_el.iter():
                if _local_name(word_el.tag) != "word":
                    continue
                text = "".join(word_el.itertext()).strip()
                if not text:
                    continue
                try:
                    x_min = float(word_el.attrib["xMin"])
                    x_max = float(word_el.attrib["xMax"])
                    y_min = float(word_el.attrib["yMin"])
                    y_max = float(word_el.attrib["yMax"])
                except (KeyError, ValueError) as exc:
                    raise ValueError(
                        f"malformed bbox word coordinates on page {page_number}: {text!r}"
                    ) from exc
                words.append(
                    {
                        "text": text,
                        "x_min": x_min,
                        "x_max": x_max,
                        "y_min": y_min,
                        "y_max": y_max,
                    }
                )
            if words:
                words.sort(key=lambda word: (float(word["x_min"]), float(word["y_min"])))
                lines.append(
                    {
                        "y_min": min(float(word["y_min"]) for word in words),
                        "x_min": min(float(word["x_min"]) for word in words),
                        "words": words,
                    }
                )
        lines.sort(key=lambda line: (float(line["y_min"]), float(line["x_min"])))
        pages.append(
            {
                "page_number": page_number,
                "width": width,
                "height": height,
                "lines": lines,
            }
        )
    if not pages:
        raise ValueError("bbox extraction returned no PDF pages")
    return pages


def _side_text(words: list[dict[str, Any]], page_width: float, side: str) -> str:
    midpoint = float(page_width) / 2.0
    if side == "left":
        selected = [
            word for word in words
            if (float(word["x_min"]) + float(word["x_max"])) / 2.0 < midpoint
        ]
    elif side == "right":
        selected = [
            word for word in words
            if (float(word["x_min"]) + float(word["x_max"])) / 2.0 >= midpoint
        ]
    else:
        raise ValueError(f"unknown side: {side}")
    selected.sort(key=lambda word: float(word["x_min"]))
    return " ".join(str(word["text"]) for word in selected).strip()


def dnp_blocks_from_bbox_pages(pages: list[dict[str, Any]]) -> dict[str, str]:
    """Extract left/right DNP text using real x coordinates, never character slicing."""
    blocks: dict[str, list[str]] = {"left": [], "right": []}
    active = {"left": False, "right": False}
    heading_counts = {"left": 0, "right": 0}
    end_counts = {"left": 0, "right": 0}

    for page in pages:
        width = float(page["width"])
        for line in page["lines"]:
            words = list(line["words"])
            for side in ("left", "right"):
                text = _side_text(words, width, side)
                if not text:
                    continue
                dnp_match = DNP_RE.search(text)
                if dnp_match:
                    heading_counts[side] += 1
                    active[side] = True
                    tail = text[dnp_match.end():].strip(" :-")
                    if tail:
                        blocks[side].append(tail)
                    continue
                if active[side] and NOT_ACTIVE_RE.search(text):
                    end_counts[side] += 1
                    active[side] = False
                    continue
                if active[side]:
                    if STOP_RE.search(text):
                        active[side] = False
                        continue
                    blocks[side].append(text)

    for side in ("left", "right"):
        if heading_counts[side] != 1:
            raise ValueError(
                f"expected exactly one coordinate DNP heading for {side}; "
                f"observed {heading_counts[side]}"
            )
        if end_counts[side] < 1:
            raise ValueError(f"coordinate DNP block for {side} did not terminate at Not Active")
    return {side: " ".join(parts).strip() for side, parts in blocks.items()}


def parse_dnp_tokens_from_bbox_pages(
    pages: list[dict[str, Any]],
    *,
    season: int,
    week: int,
    game_id: str,
    away_team: str,
    home_team: str,
) -> list[DnpToken]:
    blocks = dnp_blocks_from_bbox_pages(pages)
    tokens: list[DnpToken] = []
    for side, team in (("left", away_team), ("right", home_team)):
        seen: set[tuple[str, str]] = set()
        for match in TOKEN_RE.finditer(blocks[side]):
            jersey = normalize_jersey(match.group("jersey"))
            name = match.group("name").strip()
            if name.upper().replace(".", "") in POSITION_TOKENS:
                continue
            key = (jersey, name)
            if key in seen:
                continue
            seen.add(key)
            tokens.append(
                DnpToken(
                    season=int(season),
                    week=int(week),
                    game_id=str(game_id),
                    team=normalize_team(team),
                    side=side,
                    jersey_number=jersey,
                    gamebook_name=name,
                )
            )
    return tokens


def parse_all_dnp_tokens_bbox(
    archive_root: Path,
) -> tuple[list[DnpToken], list[dict[str, Any]]]:
    all_tokens: list[DnpToken] = []
    errors: list[dict[str, Any]] = []
    for season in TARGET_SEASONS:
        for row in read_archive_manifest(archive_root, season):
            try:
                gz_path = archive_root / str(row["raw_object_relpath"])
                raw_pdf = gzip.decompress(gz_path.read_bytes())
                if sha256_bytes(raw_pdf) != str(row["raw_pdf_sha256"]):
                    raise ValueError("raw PDF SHA mismatch against qualified archive manifest")
                pages = extract_pdf_bbox_pages(raw_pdf)
                all_tokens.extend(
                    parse_dnp_tokens_from_bbox_pages(
                        pages,
                        season=int(season),
                        week=int(row["week"]),
                        game_id=str(row["game_id"]),
                        away_team=str(row["away_team"]),
                        home_team=str(row["home_team"]),
                    )
                )
            except Exception as exc:
                errors.append(
                    {
                        "season": int(season),
                        "week": row.get("week"),
                        "game_id": row.get("game_id"),
                        "parser_version": PARSER_VERSION,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    return all_tokens, errors


__all__ = [
    "PARSER_VERSION",
    "dnp_blocks_from_bbox_pages",
    "extract_pdf_bbox_pages",
    "parse_all_dnp_tokens_bbox",
    "parse_dnp_tokens_from_bbox_pages",
]
