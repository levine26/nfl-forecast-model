from __future__ import annotations

"""Zero-authority seven-partition pre-kickoff chronology diagnostic for V09B."""

import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-MODERN-DNP-CONTRADICTION-KICKOFF-CHRONOLOGY-DIAGNOSTIC-V1"
ALIASES = {
    "00-0031288": ["AJ McCarron", "A.J. McCarron"], "00-0032891": ["Daryl Worley"],
    "00-0030069": ["Damontre Moore", "Damontre' Moore", "Damontre’ Moore"], "00-0033667": ["Cameron Hunt"],
    "00-0030520": ["Mike Glennon"], "00-0032697": ["Doug Middleton"], "00-0031503": ["Jameis Winston"],
    "00-0036303": ["Josiah Scott"], "00-0034437": ["Logan Cooke"], "00-0035656": ["Khalen Saunders"],
    "00-0027948": ["Blaine Gabbert"], "00-0028092": ["Richard Sherman"], "00-0034668": ["Aaron Stinnie"],
    "00-0036985": ["Robert Hainsey"], "00-0027793": ["Antonio Brown"], "00-0033913": ["Chris Wormley"],
}
TEAM_TZ = {"OAK": "America/Los_Angeles", "JAX": "America/New_York", "NO": "America/Chicago",
           "KC": "America/Chicago", "TB": "America/New_York", "PIT": "America/New_York"}
MONTH = {m.lower(): i for i, names in enumerate([
    (), ("Jan", "January"), ("Feb", "February"), ("Mar", "March"), ("Apr", "April"), ("May",),
    ("Jun", "June"), ("Jul", "July"), ("Aug", "August"), ("Sep", "Sept", "September"),
    ("Oct", "October"), ("Nov", "November"), ("Dec", "December")]) for m in names}
DATE_RE = re.compile(r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),\s*(\d{4})", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("’", "'")).strip()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def kind(url: str) -> str:
    p = urlparse(url).path.lower()
    if "/team/transactions/" in p: return "transaction_ledger"
    if "inactive" in p or "in-and-out" in p: return "inactive_article"
    if "/sitemap/" in p: return "sitemap"
    if "transaction" in p or "roster-move" in p or ("roster" in p and "move" in p): return "transaction_article"
    if "injury" in p: return "injury_article"
    return "article"


def first_party(url: str, allowed: set[str]) -> bool:
    p = urlparse(url)
    return p.scheme.lower() == "https" and (p.hostname or "").lower() in allowed


def pub_value(soup: BeautifulSoup, text: str) -> str | None:
    for attrs in ({"property": "article:published_time"}, {"name": "article:published_time"},
                  {"property": "og:published_time"}, {"name": "date"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"): return str(tag.get("content")).strip()
    t = soup.find("time")
    if t and t.get("datetime"): return str(t.get("datetime")).strip()
    m = re.search(DATE_RE.pattern + r"\s+at\s+(\d{1,2}):(\d{2})\s*(AM|PM)\b", text, re.I)
    return m.group(0) if m else None


def parse_pub(value: str | None) -> tuple[datetime | None, str | None, str]:
    if not value: return None, None, "missing"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo: return dt.astimezone(timezone.utc), None, "timestamp_with_timezone"
    except ValueError: pass
    m = DATE_RE.search(value)
    if not m: return None, None, "unparsed"
    date_s = f"{int(m.group(3)):04d}-{MONTH[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    return None, date_s, "date_only_or_timezone_missing"


def player_contexts(text: str, aliases: list[str], radius: int = 360) -> list[tuple[int, str, str]]:
    hay = text.lower().replace("’", "'")
    out, seen = [], set()
    for alias in aliases:
        needle, start = alias.lower().replace("’", "'"), 0
        while (idx := hay.find(needle, start)) >= 0:
            left = text.rfind("\n", 0, idx) + 1
            right = text.find("\n", idx + len(alias)); right = len(text) if right < 0 else right
            a = max(0, idx - radius); b = min(len(text), idx + len(alias) + radius)
            raw = text[a:b]; rel = idx - a
            row = (idx, norm(raw[:rel] + " <<<PLAYER>>> " + raw[rel + len(alias):]), norm(text[left:right]))
            if row not in seen: seen.add(row); out.append(row)
            start = idx + max(1, len(alias))
    return sorted(out)


def classify(source_kind: str, context: str, line: str) -> tuple[str | None, str | None]:
    c, ln, mark = context.lower().replace("’", "'"), line.lower().replace("’", "'"), "<<<player>>>"
    target = c
    if source_kind in {"transaction_ledger", "transaction_article"} and mark in c:
        pre, post = c.split(mark, 1)
        l = max(pre.rfind(";"), pre.rfind("."), pre.rfind("\n"))
        rs = [x for x in (post.find(";"), post.find("."), post.find("\n")) if x >= 0]
        r = min(rs) if rs else len(post)
        target = pre[l + 1:] + " " + mark + " " + post[:r]
    if re.search(r"\b(waived|released|terminated)\b", target): return "WAIVED_RELEASED", "NOT_APPLICABLE_NOT_ROSTER_ELIGIBLE"
    if re.search(r"\b(reserve/injured|injured reserve|reserve/covid-19|reserve/covid|reserve/pup|reserve/nfi)\b", target) and re.search(r"\b(placed|moved|put)\b", target):
        return "RESERVE_IR", "NOT_APPLICABLE_NOT_ROSTER_ELIGIBLE"
    if re.search(r"\b(signed|restored|moved)\b.{0,120}\bpractice squad\b", target) and not re.search(r"\b(promoted|elevated|activated|signed to active roster)\b", target):
        return "PRACTICE_SQUAD", "NOT_APPLICABLE_NOT_ROSTER_ELIGIBLE"
    if re.search(r"\b(promoted|elevated|activated|signed)\b.{0,140}\b(active roster|active/inactive|active status)\b", target) or re.search(r"\b(promoted|elevated|activated)\b.{0,140}\bfrom (the )?practice squad\b", target):
        return "ELEVATED_ACTIVATED", None
    if source_kind == "inactive_article":
        direct = re.search(r"<<<player>>>.{0,90}\b(inactive|deactivated|ruled out|is out)\b|\b(inactive|deactivated|ruled out|out)\b.{0,90}<<<player>>>", c)
        prefix = bool(re.match(r"^(?:#?\d{1,2}\s+)?(?:qb|rb|fb|wr|te|ol|ot|t|g|c|dl|de|dt|lb|cb|db|s|k|p|ls)\b", ln))
        list_item = mark in c and prefix and len(ln.split()) <= 6 and bool(re.search(r"\b(inactive|inactives)\b", c))
        if direct or list_item: return "PROVABLY_ROSTER_ELIGIBLE_BEFORE_KICKOFF", "EXPLICIT_INACTIVE"
    return None, None


def ledger_date(text: str, pos: int, season: int) -> str | None:
    hits = list(re.finditer(r"\b(\d{1,2})/(\d{1,2})\b", text[max(0, pos - 180):pos]))
    if not hits: return None
    m = hits[-1]
    return f"{season:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"


def before_kickoff(event_dt: datetime | None, event_date: str | None, kickoff: datetime, game_tz: str) -> tuple[bool, str | None]:
    if event_dt and event_dt.tzinfo: return (event_dt < kickoff, None if event_dt < kickoff else "event_not_before_kickoff")
    if event_date:
        d = datetime.fromisoformat(event_date).date(); gd = kickoff.astimezone(ZoneInfo(game_tz)).date()
        if d < gd: return True, None
        return False, "same_day_date_without_ordering" if d == gd else "event_after_game_date"
    return False, "event_chronology_unresolved"


def discover(seed: str, soup: BeautifulSoup, limit: int = 10) -> list[str]:
    host, out = (urlparse(seed).hostname or "").lower(), []
    for a in soup.find_all("a", href=True):
        u = urljoin(seed, str(a.get("href") or "")); label = norm(a.get_text(" ", strip=True)).lower()
        if (urlparse(u).hostname or "").lower() == host and ("inactive" in label or "inactive" in urlparse(u).path.lower()) and u not in out:
            out.append(u)
        if len(out) >= limit: break
    return out


def get(url: str, timeout: float):
    try:
        return requests.get(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-kickoff-chronology/1.0)", "Accept": "text/html,application/xhtml+xml"}), None
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:500]}"


def run(contract_path: Path, outdir: Path, timeout: float) -> dict[str, Any]:
    c = json.loads(contract_path.read_text()); ps = c["frozen_scope"]["partitions"]
    if c.get("contract_id") != CONTRACT_ID or len(ps) != 7 or sum(len(p["dnp_rows"]) for p in ps) != 17: raise ValueError("frozen contract accounting changed")
    outdir.mkdir(parents=True, exist_ok=True); rawdir = outdir / "raw_sources"; rawdir.mkdir(exist_ok=True)
    allowed = {x.lower() for x in c["source_policy"]["allowed_authority_hosts"]}
    manifest, events, sid_n = [], {}, 0
    for p in ps:
        kickoff = datetime.fromisoformat(p["kickoff_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
        tz = TEAM_TZ[p["team"]]; season = int(p["game_id"][:4]); q = [(u, "frozen_seed") for u in p.get("source_seeds", [])]; seen = set()
        while q:
            url, basis = q.pop(0)
            if url in seen: continue
            seen.add(url); sid_n += 1; sid = f"S{sid_n:03d}"; resp, err = get(url, timeout)
            m = {"source_id": sid, "partition_key": p["partition_key"], "requested_url": url, "source_kind": kind(url), "discovery_basis": basis,
                 "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "http_status": None, "final_url": None, "first_party": False,
                 "raw_sha256": None, "raw_bytes": 0, "publication_raw": None, "publication_time_utc": None, "publication_precision": "missing",
                 "fetch_error": err, "eligible_first_party_source": False, "rejection_reason": None}
            if resp is None: m["rejection_reason"] = "fetch_error"; manifest.append(m); continue
            raw = resp.content; m.update(http_status=int(resp.status_code), final_url=str(resp.url), raw_sha256=sha(raw), raw_bytes=len(raw), first_party=first_party(str(resp.url), allowed))
            rp = rawdir / f"{sid}_{m['raw_sha256']}.html"; rp.write_bytes(raw); m["raw_relpath"] = str(rp.relative_to(outdir))
            if resp.status_code >= 400: m["rejection_reason"] = f"HTTP_{resp.status_code}"
            elif not m["first_party"]: m["rejection_reason"] = "final_url_not_first_party"
            else: m["eligible_first_party_source"] = True
            soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser"); text = soup.get_text("\n", strip=True)
            if m["eligible_first_party_source"] and m["source_kind"] == "sitemap":
                for u in discover(str(resp.url), soup):
                    if u not in seen and all(u != z[0] for z in q): q.append((u, f"one_hop_from:{sid}"))
            pv = pub_value(soup, text); pdt, pdate, pprec = parse_pub(pv); m["publication_raw"], m["publication_precision"] = pv, pprec
            if pdt: m["publication_time_utc"] = pdt.isoformat()
            for pl in p["dnp_rows"]:
                gid = str(pl["gsis_id"])
                for pos, ctx, line in player_contexts(text, ALIASES[gid]):
                    rs, ds = classify(m["source_kind"], ctx, line)
                    if not rs and not ds: continue
                    edt, edate = pdt, pdate
                    if m["source_kind"] == "transaction_ledger": edt, edate = None, ledger_date(text, pos, season)
                    ok, reject = before_kickoff(edt, edate, kickoff, tz)
                    if not m["eligible_first_party_source"]: ok, reject = False, m["rejection_reason"] or "source_not_eligible"
                    ev = {"source_id": sid, "source_url": str(resp.url), "event_time_utc": edt.isoformat() if edt else None, "event_date": edate,
                          "roster_state": rs, "designation_state": ds, "evidence": ctx[:1200], "authoritative_pre_kickoff": ok, "rejection_reason": reject}
                    events.setdefault((p["partition_key"], gid), []).append(ev)
            manifest.append(m)
    rows, parts, rejected = [], [], []
    for p in ps:
        n_nonactive = 0
        for pl in p["dnp_rows"]:
            es = events.get((p["partition_key"], str(pl["gsis_id"])), []); auth = [e for e in es if e["authoritative_pre_kickoff"]]
            rejected.extend({"partition_key": p["partition_key"], "gsis_id": pl["gsis_id"], **e} for e in es if not e["authoritative_pre_kickoff"])
            auth.sort(key=lambda e: (e["event_time_utc"] or e["event_date"] or "", e["source_id"]))
            rs, ds, support = "UNRESOLVED_CHRONOLOGY", "UNRESOLVED_DESIGNATION", []
            for e in auth:
                if e["roster_state"]: rs = e["roster_state"]
                if e["designation_state"]: ds = e["designation_state"]
                support.append(e["source_id"])
            if rs == "ELEVATED_ACTIVATED": rs = "PROVABLY_ROSTER_ELIGIBLE_BEFORE_KICKOFF"
            if ds == "EXPLICIT_INACTIVE": rs = "PROVABLY_ROSTER_ELIGIBLE_BEFORE_KICKOFF"
            if ds in {"EXPLICIT_INACTIVE", "NOT_APPLICABLE_NOT_ROSTER_ELIGIBLE"} or rs in {"WAIVED_RELEASED", "RESERVE_IR", "PRACTICE_SQUAD", "PROVABLY_NOT_ROSTER_ELIGIBLE_BEFORE_KICKOFF"}: n_nonactive += 1
            rows.append({"partition_key": p["partition_key"], "game_id": p["game_id"], "team": p["team"], "kickoff_utc": p["kickoff_utc"], **pl,
                         "roster_eligibility_state": rs, "game_day_designation_state": ds, "supporting_source_ids": sorted(set(support)), "authoritative_events": auth,
                         "unresolved_reason": None if auth else "no explicit first-party pre-kickoff evidence from frozen source discovery", "membership_qualification_authority": False})
        req = int(p["minimum_dnp_non_active_required_by_active_max"])
        parts.append({"partition_key": p["partition_key"], "active_max_contradiction": bool(p["active_max_contradiction"]),
                      "minimum_dnp_non_active_required_by_active_max": req, "explicit_non_active_dnp_rows": n_nonactive,
                      "active_max_contradiction_descriptively_explained": (n_nonactive >= req) if p["active_max_contradiction"] else None,
                      "total_roster_max_contradiction": bool(p["total_roster_max_contradiction"]), "qualification_authority": False})
    expected = {(p["partition_key"], str(x["gsis_id"])) for p in ps for x in p["dnp_rows"]}; got = {(r["partition_key"], str(r["gsis_id"])) for r in rows}
    integrity = len(rows) == 17 and got == expected and len(parts) == 7
    result = {"diagnostic_version": 1, "contract_id": CONTRACT_ID, "status": "DIAGNOSTIC_COMPLETE_ZERO_QUALIFICATION_AUTHORITY" if integrity else "DIAGNOSTIC_ACCOUNTING_FAILURE",
              "accounting_integrity_pass": integrity, "source_manifest": manifest, "chronology_rows": rows, "partition_diagnostics": parts, "rejected_evidence": rejected[:200],
              "aggregate": {"partitions": 7, "dnp_rows": 17, "sources_attempted": len(manifest), "rows_with_any_authoritative_event": sum(bool(r["authoritative_events"]) for r in rows),
                            "rows_unresolved_without_authoritative_event": sum(not r["authoritative_events"] for r in rows), "active_max_partitions_total": 6,
                            "active_max_partitions_descriptively_explained": sum(x["active_max_contradiction_descriptively_explained"] is True for x in parts)},
              "authority": {"diagnostic_has_membership_qualification_authority": False, "modern_player_team_game_identity_qualified": True,
                            "modern_game_day_roster_universe_qualified": False, "training_label_semantics_qualified": False, "training_source_chronology_qualified": False,
                            "v09b_model_fit_authorized": False, "production_dependency_authorized": False},
              "governance": {"weekly_roster_status_used_as_authority": False, "absence_from_inactive_used_as_positive": False,
                             "postgame_participation_used_as_training_authority": False, "game_outcomes_used": 0, "completed_2026_outcomes_used": 0, "model_fit_performed": False}}
    (outdir / "diagnostic_report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if not integrity: raise RuntimeError("frozen accounting integrity failed")
    return result


def main(argv: Iterable[str] | None = None) -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--contract", type=Path, required=True); ap.add_argument("--output-dir", type=Path, required=True); ap.add_argument("--timeout", type=float, default=60.0)
    a = ap.parse_args(list(argv) if argv is not None else None); r = run(a.contract, a.output_dir, a.timeout); print(json.dumps({"status": r["status"], **r["aggregate"]}, indent=2))


if __name__ == "__main__": main()
