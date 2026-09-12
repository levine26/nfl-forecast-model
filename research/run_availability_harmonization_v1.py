from __future__ import annotations

"""Run the research-only 2022-2025 availability harmonization audit."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess

import nflreadpy as nfl
import pandas as pd
import requests

from nfl_forecast.data import configure_cache
from research.availability_harmonization_v1 import (
    TARGET_SEASONS,
    evaluate_harmonization,
    harmonize_season,
    validate_injury_asset,
    validate_v09b_preregistry,
)


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(
    *,
    cache_dir: str = ".cache/nflreadpy",
    output_dir: str = "research_outputs/availability_harmonization_v1",
    contract_path: str = "research/availability/harmonization_contract_v1.json",
    experiments_path: str = "research/experiments.json",
    receipt_2025_path: str = "research/availability/2025_reconstruction_qualification_v1.json",
    session=requests,
) -> dict:
    contract = _load_json(contract_path)
    registry = _load_json(experiments_path)
    receipt_2025 = _load_json(receipt_2025_path)
    targets = [int(x) for x in contract.get("target_seasons", TARGET_SEASONS)]

    configure_cache(cache_dir)
    schedules = _pandas(nfl.load_schedules(targets))
    if schedules is None or schedules.empty:
        raise RuntimeError("nflreadpy returned no schedules for harmonization target seasons")

    canonical_parts: list[pd.DataFrame] = []
    audits = []
    source_manifest = []
    url_template = contract["source"]["url_template"]
    expected_rows = contract["source"]["expected_full_asset_rows"]
    expected_hashes = contract["source"]["expected_sha256"]

    for season in targets:
        key = str(season)
        url = url_template.format(season=season)
        response = session.get(
            url,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; nfl-forecast-model-research/1.0)",
                "Accept": "text/csv,text/plain,*/*",
            },
        )
        response.raise_for_status()
        frame, digest = validate_injury_asset(
            response.content,
            season=season,
            expected_rows=int(expected_rows[key]),
            expected_sha256=expected_hashes.get(key),
        )
        canonical, audit = harmonize_season(
            frame,
            schedules,
            season=season,
            source_sha256=digest,
        )
        unmatched = (
            canonical.loc[canonical["game_id"].isna(), ["week", "team"]]
            .drop_duplicates()
            .sort_values(["week", "team"], kind="stable")
            .to_dict("records")
        )
        unmatched_rows = int(canonical["game_id"].isna().sum())
        canonical_parts.append(canonical)
        audits.append(audit)
        source_manifest.append(
            {
                "season": season,
                "url": url,
                "sha256": digest,
                "full_asset_rows": len(frame),
                "regular_rows": len(canonical),
                "hash_pinned_in_contract": expected_hashes.get(key) is not None,
                "schedule_unmatched_rows": unmatched_rows,
                "schedule_unmatched_team_weeks": unmatched,
            }
        )

    prereg_ok, prereg_reasons = validate_v09b_preregistry(registry)
    report = evaluate_harmonization(
        audits,
        contract,
        v09b_prereg_ok=prereg_ok,
        qualified_2025_receipt=receipt_2025,
    )
    report.update(
        {
            "mode": "research_only_schema_chronology_harmonization",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": _git_sha(),
            "contract_path": contract_path,
            "preregistration_drift_reasons": prereg_reasons,
            "source_manifest": source_manifest,
            "environment": {
                "python": platform.python_version(),
                "pandas": pd.__version__,
            },
        }
    )

    canonical_all = pd.concat(canonical_parts, ignore_index=True)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    canonical_all.to_csv(out / "harmonized_practice_state_2022_2025.csv", index=False)
    pd.DataFrame([audit.as_dict() for audit in audits]).to_csv(
        out / "season_audits.csv", index=False
    )
    (out / "source_manifest.json").write_text(
        json.dumps(source_manifest, indent=2), encoding="utf-8"
    )
    (out / "qualification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default=".cache/nflreadpy")
    parser.add_argument(
        "--output-dir", default="research_outputs/availability_harmonization_v1"
    )
    parser.add_argument(
        "--contract", default="research/availability/harmonization_contract_v1.json"
    )
    args = parser.parse_args()
    run(cache_dir=args.cache_dir, output_dir=args.output_dir, contract_path=args.contract)


if __name__ == "__main__":
    main()
