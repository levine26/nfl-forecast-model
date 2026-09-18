from __future__ import annotations

import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

import pandas as pd

YEARS = (2023, 2024, 2025)
URL = (
    "https://raw.githubusercontent.com/gcampb41/nfl_data-/main/"
    "data/processed/football/nfl/player_props/{year}.parquet"
)


def download(url: str, target: Path) -> None:
    req = Request(url, headers={"User-Agent": "LevLine-Props-Historical-Audit/1.0"})
    with urlopen(req, timeout=120) as response:
        target.write_bytes(response.read())


def safe_counts(frame: pd.DataFrame, column: str, limit: int = 30):
    if column not in frame.columns:
        return None
    values = frame[column].astype("string").fillna("<NA>").value_counts(dropna=False)
    return {str(k): int(v) for k, v in values.head(limit).items()}


def main() -> int:
    output = {
        "source_repository": "gcampb41/nfl_data-",
        "source_upstream": "theedgepredictor/odds-data-pump",
        "source_documented_provider": "Action Network",
        "years": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for year in YEARS:
            path = root / f"{year}.parquet"
            download(URL.format(year=year), path)
            frame = pd.read_parquet(path)
            info = {
                "rows": int(len(frame)),
                "columns": list(frame.columns),
                "dtypes": {c: str(frame[c].dtype) for c in frame.columns},
                "weeks": sorted(
                    int(x) for x in pd.to_numeric(frame.get("week"), errors="coerce").dropna().unique()
                ) if "week" in frame.columns else [],
                "season_values": sorted(
                    int(x) for x in pd.to_numeric(frame.get("season"), errors="coerce").dropna().unique()
                ) if "season" in frame.columns else [],
                "bet_type_counts": safe_counts(frame, "bet_type", 100),
                "book_id_counts": safe_counts(frame, "book_id", 30),
                "side_counts": safe_counts(frame, "side", 20),
                "line_type_counts": safe_counts(frame, "line_type", 20),
                "position_counts": safe_counts(frame, "position", 20),
                "position_group_counts": safe_counts(frame, "position_group", 20),
                "nonnull": {
                    c: int(frame[c].notna().sum())
                    for c in (
                        "event_id", "player_id", "action_network_player_id",
                        "team", "position", "position_group", "value", "odds",
                        "book_id", "side", "bet_type", "week", "season"
                    )
                    if c in frame.columns
                },
                "unique": {
                    c: int(frame[c].nunique(dropna=True))
                    for c in (
                        "event_id", "player_id", "action_network_player_id",
                        "team", "bet_type", "book_id"
                    )
                    if c in frame.columns
                },
                "sample": frame.head(5).astype(object).where(pd.notna(frame.head(5)), None).to_dict("records"),
            }
            output["years"][str(year)] = info

    out_path = Path("research_outputs/props_accuracy/historical_source_audit.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
