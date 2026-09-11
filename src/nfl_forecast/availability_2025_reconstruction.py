from __future__ import annotations

"""Research-only 2025 historical availability reconstruction.

Stable player identity and weekly report state come from the pinned nflverse 2025 injury
asset. Official NFL.com historical injury pages provide the independent all-22-week
status cross-check; the immutable FootballDB-derived GitHub mirror is supplemental source
evidence only. The NFL's required Game Status Report day is used conservatively to prove
the final practice-report state existed before T-120. Actual snaps, participation,
outcomes, and game-day inactives are never substitutes.
"""

from dataclasses import dataclass
from datetime import timedelta
import hashlib
from io import StringIO
import re
import unicodedata
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import pandas as pd


NFLVERSE_EXPECTED_SHA256 = "873ca1606dd575bd01152508a243ef6b3a0f8f97b90b707217e62ee8c7ceb735"
NFLVERSE_EXPECTED_ROWS = 6068
REGULAR_MIRROR_EXPECTED_GIT_BLOB_SHA1 = "24568d807792e04739d17b2421e5e6f62cc74d68"
REQUIRED_NFLVERSE_COLUMNS = {
    "season", "season_type", "game_type", "team", "week", "gsis_id", "position",
    "full_name", "first_name", "last_name", "report_primary_injury",
    "report_secondary_injury", "report_status", "practice_primary_injury",
    "practice_secondary_injury", "practice_status",
}
REQUIRED_MIRROR_COLUMNS = {
    "season", "week", "team", "player", "position", "injury",
    "day_1_date", "day_1_status", "day_2_date", "day_2_status",
    "day_3_date", "day_3_status", "game_status",
}

TEAM_NAME_TO_ABBR = {
    "Arizona Cardinals": "ARI", "Cardinals": "ARI", "Atlanta Falcons": "ATL", "Falcons": "ATL",
    "Baltimore Ravens": "BAL", "Ravens": "BAL", "Buffalo Bills": "BUF", "Bills": "BUF",
    "Carolina Panthers": "CAR", "Panthers": "CAR", "Chicago Bears": "CHI", "Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Bengals": "CIN", "Cleveland Browns": "CLE", "Browns": "CLE",
    "Dallas Cowboys": "DAL", "Cowboys": "DAL", "Denver Broncos": "DEN", "Broncos": "DEN",
    "Detroit Lions": "DET", "Lions": "DET", "Green Bay Packers": "GB", "Packers": "GB",
    "Houston Texans": "HOU", "Texans": "HOU", "Indianapolis Colts": "IND", "Colts": "IND",
    "Jacksonville Jaguars": "JAX", "Jaguars": "JAX", "Kansas City Chiefs": "KC", "Chiefs": "KC",
    "Las Vegas Raiders": "LV", "Raiders": "LV", "Los Angeles Chargers": "LAC", "Chargers": "LAC",
    "Los Angeles Rams": "LA", "Rams": "LA", "Miami Dolphins": "MIA", "Dolphins": "MIA",
    "Minnesota Vikings": "MIN", "Vikings": "MIN", "New England Patriots": "NE", "Patriots": "NE",
    "New Orleans Saints": "NO", "Saints": "NO", "New York Giants": "NYG", "Giants": "NYG",
    "New York Jets": "NYJ", "Jets": "NYJ", "Philadelphia Eagles": "PHI", "Eagles": "PHI",
    "Pittsburgh Steelers": "PIT", "Steelers": "PIT", "San Francisco 49ers": "SF", "49ers": "SF",
    "Seattle Seahawks": "SEA", "Seahawks": "SEA", "Tampa Bay Buccaneers": "TB", "Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Titans": "TEN", "Washington Commanders": "WAS", "Commanders": "WAS",
}
TEAM_ABBR_ALIASES = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS"}
GAME_STATUS_REPORT_DAYS_BEFORE = {"Monday": 2, "Wednesday": 1, "Thursday": 1, "Friday": 1, "Saturday": 2, "Sunday": 2}
VALID_TEAMS = set(TEAM_NAME_TO_ABBR.values())


@dataclass(frozen=True)
class ReconstructionSummary:
    nflverse_rows: int
    external_rows: int
    nfl_regular_weeks_crosschecked: int
    nfl_postseason_pages: int
    identity_match_rate: float
    practice_status_agreement_rate: float
    game_status_agreement_rate: float
    known_by_t120_rate: float
    fully_qualified_practice_state_rate: float
    qualified: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "nflverse_rows": self.nflverse_rows,
            "external_rows": self.external_rows,
            "nfl_regular_weeks_crosschecked": self.nfl_regular_weeks_crosschecked,
            "nfl_postseason_pages": self.nfl_postseason_pages,
            "identity_match_rate": self.identity_match_rate,
            "practice_status_agreement_rate": self.practice_status_agreement_rate,
            "game_status_agreement_rate": self.game_status_agreement_rate,
            "known_by_t120_rate": self.known_by_t120_rate,
            "fully_qualified_practice_state_rate": self.fully_qualified_practice_state_rate,
            "qualified": self.qualified,
            "reasons": list(self.reasons),
            "historical_game_status_feature_authorized": False,
            "postgame_participation_used": 0,
            "actual_snaps_used": 0,
            "completed_2026_outcomes_used": 0,
        }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def normalize_team(value: object) -> str:
    text = str(value or "").strip()
    return TEAM_ABBR_ALIASES.get(text, TEAM_NAME_TO_ABBR.get(text, text))


def normalize_name_token(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("-", " ").lower()
    text = re.sub(r"\b(jr|sr|ii|iii|iv)\.?$", "", text).strip()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    parts = text.split()
    leading_initials = 0
    while leading_initials < len(parts) and len(parts[leading_initials]) == 1:
        leading_initials += 1
    if leading_initials >= 2:
        parts = ["".join(parts[:leading_initials]), *parts[leading_initials:]]
    return " ".join(parts)


def normalize_practice_status(value: object) -> str:
    text = normalize_name_token(value)
    if not text or text in {"nan", "none", "na", "not listed", "not reported", ""}:
        return ""
    if text in {"fp", "full", "full participation in practice"} or "full participation" in text:
        return "full"
    if text in {"lp", "limited", "limited participation in practice"} or "limited participation" in text:
        return "limited"
    if text == "dnp" or "did not participate" in text:
        return "dnp"
    return text


def normalize_game_status(value: object) -> str:
    text = normalize_name_token(value)
    if not text or text in {"nan", "none", "na", "unspecified"}:
        return ""
    if text.startswith("out"):
        return "out"
    if text.startswith("doubtful"):
        return "doubtful"
    if text.startswith("questionable"):
        return "questionable"
    return text


def validate_nflverse_payload(payload: bytes) -> pd.DataFrame:
    digest = sha256_bytes(payload)
    if digest != NFLVERSE_EXPECTED_SHA256:
        raise ValueError(f"2025 nflverse injury asset digest changed: expected {NFLVERSE_EXPECTED_SHA256}, got {digest}")
    frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
    missing = REQUIRED_NFLVERSE_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"2025 nflverse injury asset missing fields: {sorted(missing)}")
    if len(frame) != NFLVERSE_EXPECTED_ROWS:
        raise ValueError(f"2025 nflverse injury row count changed: expected {NFLVERSE_EXPECTED_ROWS}, got {len(frame)}")
    frame = frame[pd.to_numeric(frame["season"], errors="coerce").eq(2025)].copy()
    if len(frame) != NFLVERSE_EXPECTED_ROWS:
        raise ValueError("nflverse injury asset contains rows outside season 2025")
    if frame["gsis_id"].isna().any() or frame["gsis_id"].astype(str).str.strip().eq("").any():
        raise ValueError("2025 nflverse injury asset has missing stable GSIS identity")
    weeks = set(pd.to_numeric(frame["week"], errors="coerce").dropna().astype(int))
    if weeks != set(range(1, 23)):
        raise ValueError(f"2025 nflverse injury weeks changed: {sorted(weeks)}")
    return frame


def _final_nonempty_status(row: pd.Series) -> str:
    for column in ("day_3_status", "day_2_status", "day_1_status"):
        value = row.get(column, "")
        if pd.notna(value) and normalize_name_token(value):
            return str(value)
    return ""


def load_regular_mirror(payload: bytes, *, source_url: str) -> pd.DataFrame:
    """Load the pinned supplemental mirror without treating it as a completeness gate."""
    digest = git_blob_sha1(payload)
    if digest != REGULAR_MIRROR_EXPECTED_GIT_BLOB_SHA1:
        raise ValueError(f"regular injury-report mirror identity changed: expected git blob {REGULAR_MIRROR_EXPECTED_GIT_BLOB_SHA1}, got {digest}")
    frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
    missing = REQUIRED_MIRROR_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"regular mirror missing fields: {sorted(missing)}")
    frame = frame[pd.to_numeric(frame["season"], errors="coerce").eq(2025)].copy()
    frame["week"] = pd.to_numeric(frame["week"], errors="raise").astype(int)
    frame = frame[frame["week"].between(1, 18)].copy()
    if frame.empty:
        raise ValueError("regular mirror has no 2025 regular-season rows")
    frame["team"] = frame["team"].map(normalize_team)
    frame["external_player"] = frame["player"].astype(str).str.strip()
    frame["external_position"] = frame["position"].fillna("").astype(str)
    frame["external_injury"] = frame["injury"].fillna("").astype(str)
    frame["external_practice_status"] = frame.apply(_final_nonempty_status, axis=1)
    frame["external_game_status"] = frame["game_status"].fillna("").astype(str)
    frame["external_source"] = "footballdb_regular_github_mirror"
    frame["source_url"] = source_url
    return frame[["season", "week", "team", "external_player", "external_position", "external_injury", "external_practice_status", "external_game_status", "external_source", "source_url"]].copy()


def parse_nfl_postseason_page(html: str, *, nfl_week: int, source_url: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    for table in soup.find_all("table", class_=lambda value: value and "d3-o-table" in str(value)):
        section = table.find_parent(
            "section", class_=lambda value: value and "nfl-o-injury-report__unit" in str(value)
        )
        team_node = table.find_previous(
            "div", class_=lambda value: value and "nfl-t-stats__title" in str(value)
        )
        if team_node is not None and section is not None:
            team_section = team_node.find_parent(
                "section", class_=lambda value: value and "nfl-o-injury-report__unit" in str(value)
            )
            if team_section is not section:
                team_node = None
        if team_node is None:
            team_node = table.find_previous(
                "div", class_=lambda value: value and "d3-o-section-sub-title" in str(value)
            )
            if team_node is not None and section is not None:
                team_section = team_node.find_parent(
                    "section", class_=lambda value: value and "nfl-o-injury-report__unit" in str(value)
                )
                if team_section is not section:
                    team_node = None
        if team_node is None:
            team_node = table.find_previous(
                "a", class_=lambda value: value and "team-fullname" in str(value)
            )
            if team_node is not None and section is not None:
                team_section = team_node.find_parent(
                    "section", class_=lambda value: value and "nfl-o-injury-report__unit" in str(value)
                )
                if team_section is not section:
                    team_node = None
        if team_node is None:
            continue
        team = normalize_team(team_node.get_text(" ", strip=True))
        if team not in VALID_TEAMS:
            continue
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody is not None else table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            player = cells[0].get_text(" ", strip=True)
            if not player:
                continue
            records.append({
                "season": 2025, "week": nfl_week, "team": team,
                "external_player": player,
                "external_position": cells[1].get_text(" ", strip=True),
                "external_injury": cells[2].get_text(" ", strip=True),
                "external_practice_status": cells[3].get_text(" ", strip=True),
                "external_game_status": cells[4].get_text(" ", strip=True),
                "external_source": "nfl_com_official_injury_page", "source_url": source_url,
            })
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        raise ValueError(f"NFL.com injury page {source_url} parsed zero injury rows")
    return frame


def _external_identity_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["full_name_key"] = out["external_player"].map(normalize_name_token)
    split = out["full_name_key"].str.split()
    out["first_initial"] = split.map(lambda parts: parts[0][:1] if parts else "")
    out["last_name_key"] = split.map(lambda parts: parts[-1] if parts else "")
    abbreviated = out["external_player"].astype(str).str.extract(r"^\s*([A-Za-z])\.\s*(.+?)\s*$")
    mask = abbreviated[0].notna() & ~abbreviated[1].str.contains(r"\.", regex=True, na=False)
    out.loc[mask, "first_initial"] = abbreviated.loc[mask, 0].str.lower()
    out.loc[mask, "last_name_key"] = abbreviated.loc[mask, 1].map(normalize_name_token)
    out.loc[mask, "full_name_key"] = ""
    return out


def attach_stable_identity(external: pd.DataFrame, nflverse: pd.DataFrame) -> pd.DataFrame:
    ext = _external_identity_keys(external)
    nfl = nflverse.copy()
    nfl["team"] = nfl["team"].map(normalize_team)
    nfl["full_name_key"] = nfl["full_name"].map(normalize_name_token)
    nfl["first_initial"] = nfl["first_name"].astype(str).str.strip().str[:1].str.lower()
    nfl["last_name_key"] = nfl["last_name"].map(normalize_name_token)
    full_lookup = nfl.groupby(["season", "week", "team", "full_name_key"], dropna=False)["gsis_id"].agg(lambda s: tuple(sorted(set(map(str, s))))).to_dict()
    fallback_lookup = nfl.groupby(["season", "week", "team", "first_initial", "last_name_key"], dropna=False)["gsis_id"].agg(lambda s: tuple(sorted(set(map(str, s))))).to_dict()
    ids, states, methods = [], [], []
    for row in ext.itertuples(index=False):
        if str(row.full_name_key):
            candidates = full_lookup.get(
                (int(row.season), int(row.week), str(row.team), str(row.full_name_key)), ()
            )
            method = "exact_full_name"
        else:
            candidates = fallback_lookup.get(
                (int(row.season), int(row.week), str(row.team), str(row.first_initial), str(row.last_name_key)), ()
            )
            method = "unique_initial_surname"
        if len(candidates) == 1:
            ids.append(candidates[0]); states.append("unique"); methods.append(method)
        elif len(candidates) > 1:
            ids.append(""); states.append("ambiguous"); methods.append(method)
        else:
            ids.append(""); states.append("unmatched"); methods.append(method)
    ext["gsis_id"] = ids
    ext["identity_match_state"] = states
    ext["identity_match_method"] = methods
    return ext


def _kickoff_index(schedules: pd.DataFrame) -> pd.DataFrame:
    required = {"season", "week", "home_team", "away_team", "gameday", "gametime", "game_id"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"schedule missing reconstruction fields: {sorted(missing)}")
    games = schedules[pd.to_numeric(schedules["season"], errors="coerce").eq(2025)].copy()
    stamp = pd.to_datetime(games["gameday"].astype(str) + " " + games["gametime"].fillna("00:00").astype(str), errors="coerce")
    games["kickoff_utc"] = stamp.dt.tz_localize("America/New_York", ambiguous="raise", nonexistent="raise").dt.tz_convert("UTC")
    if games["kickoff_utc"].isna().any():
        raise ValueError("one or more 2025 schedule kickoff timestamps are not parseable")
    eastern = ZoneInfo("America/New_York")
    deadlines = []
    for kickoff in games["kickoff_utc"]:
        local = kickoff.tz_convert(eastern)
        weekday = local.day_name()
        if weekday not in GAME_STATUS_REPORT_DAYS_BEFORE:
            raise ValueError(f"unsupported NFL game weekday for report chronology: {weekday}")
        report_day = local.date() - timedelta(days=GAME_STATUS_REPORT_DAYS_BEFORE[weekday])
        deadlines.append(pd.Timestamp(report_day, tz=eastern) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
    games["report_deadline_eod_utc"] = pd.DatetimeIndex(deadlines).tz_convert("UTC")
    home = games[["game_id", "season", "week", "home_team", "kickoff_utc", "report_deadline_eod_utc"]].rename(columns={"home_team": "team"})
    away = games[["game_id", "season", "week", "away_team", "kickoff_utc", "report_deadline_eod_utc"]].rename(columns={"away_team": "team"})
    out = pd.concat([home, away], ignore_index=True)
    out["team"] = out["team"].map(normalize_team)
    if out.duplicated(["season", "week", "team"]).any():
        raise ValueError("2025 schedule contains ambiguous team-week game identity")
    return out


def build_canonical_reconstruction(nflverse: pd.DataFrame, external_reports: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    matched = attach_stable_identity(external_reports, nflverse)
    unique = matched[matched["identity_match_state"].eq("unique")].copy()
    if unique.duplicated(["season", "week", "team", "gsis_id"]).any():
        raise ValueError("external reports contain duplicate stable player-week rows")
    stable_cols = ["season", "week", "team", "gsis_id", "position", "full_name", "first_name", "last_name", "practice_primary_injury", "practice_secondary_injury", "practice_status", "report_primary_injury", "report_secondary_injury", "report_status", "game_type", "season_type"]
    base = nflverse[stable_cols].copy()
    base["team"] = base["team"].map(normalize_team)
    ext_cols = ["season", "week", "team", "gsis_id", "external_player", "external_position", "external_injury", "external_practice_status", "external_game_status", "external_source", "source_url", "identity_match_method"]
    out = base.merge(unique[ext_cols], on=["season", "week", "team", "gsis_id"], how="left", validate="one_to_one")
    out["identity_matched"] = out["external_player"].notna()
    out["nflverse_practice_normalized"] = out["practice_status"].map(normalize_practice_status)
    out["external_practice_normalized"] = out["external_practice_status"].map(normalize_practice_status)
    out["nflverse_game_normalized"] = out["report_status"].map(normalize_game_status)
    out["external_game_normalized"] = out["external_game_status"].map(normalize_game_status)
    out["practice_status_agrees"] = out["identity_matched"] & out["nflverse_practice_normalized"].eq(out["external_practice_normalized"])
    out["game_status_agrees"] = out["identity_matched"] & out["nflverse_game_normalized"].eq(out["external_game_normalized"])
    out = out.merge(_kickoff_index(schedules), on=["season", "week", "team"], how="left", validate="many_to_one")
    out["t120_utc"] = out["kickoff_utc"] - pd.Timedelta(minutes=120)
    out["known_by_t120"] = out["identity_matched"] & out["report_deadline_eod_utc"].notna() & out["t120_utc"].notna() & out["report_deadline_eod_utc"].le(out["t120_utc"])
    out["fully_qualified_practice_state"] = out["identity_matched"] & out["known_by_t120"] & out["practice_status_agrees"]
    out["availability_source"] = "nflverse_2025+independent_historical_report_crosscheck"
    out["chronology_policy"] = "official_game_status_report_day_eod_eastern_before_t120"
    out["historical_game_status_feature_authorized"] = False
    out["postgame_information_used"] = False
    return out


def summarize_reconstruction(canonical: pd.DataFrame, external_reports: pd.DataFrame, *, postseason_pages: int) -> ReconstructionSummary:
    total = len(canonical)
    if total == 0:
        raise ValueError("canonical 2025 reconstruction is empty")
    regular_weeks = len(set(pd.to_numeric(external_reports.loc[pd.to_numeric(external_reports["week"], errors="coerce").le(18), "week"], errors="coerce").dropna().astype(int)))
    matched = canonical["identity_matched"]
    identity_rate = float(matched.mean())
    matched_frame = canonical[matched].copy()
    practice_rate = float(matched_frame["practice_status_agrees"].mean()) if len(matched_frame) else 0.0
    game_rate = float(matched_frame["game_status_agrees"].mean()) if len(matched_frame) else 0.0
    known_rate = float(matched_frame["known_by_t120"].mean()) if len(matched_frame) else 0.0
    qualified_rate = float(canonical["fully_qualified_practice_state"].mean())
    reasons = []
    if total != NFLVERSE_EXPECTED_ROWS: reasons.append("nflverse_row_count_changed")
    if regular_weeks != 18: reasons.append("nfl_regular_week_coverage_incomplete")
    if postseason_pages != 4: reasons.append("nfl_postseason_page_coverage_incomplete")
    if identity_rate < 0.995: reasons.append("identity_match_rate_below_preregistered_gate")
    if practice_rate < 0.985: reasons.append("practice_status_agreement_below_preregistered_gate")
    if game_rate < 0.985: reasons.append("game_status_agreement_below_preregistered_gate")
    if known_rate < 1.0: reasons.append("one_or_more_matched_rows_not_proven_known_by_t120")
    if qualified_rate < 0.99: reasons.append("fully_qualified_practice_state_rate_below_preregistered_gate")
    return ReconstructionSummary(total, len(external_reports), regular_weeks, postseason_pages, identity_rate, practice_rate, game_rate, known_rate, qualified_rate, not reasons, tuple(reasons))
