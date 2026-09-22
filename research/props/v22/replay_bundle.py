from __future__ import annotations

"""Build and verify deterministic Props 2.2 prospective replay bundles.

A replay bundle preserves the exact frozen integration manifests plus the code identity
needed to regenerate the Monte Carlo samples later. It does not alter forecasts.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_manifest import (  # noqa: E402
    payload_sha256,
    verify_manifest_fingerprint,
    verify_manifest_slate_index,
)


CONTRACT_VERSION = "levline-props22-replay-bundle-v0.1"
ARCHIVE_NAME = "replay_bundle.zip"
INDEX_NAME = "replay_index.json"
CODE_PATHS = (
    "src/nfl_forecast/challenger_props_simulation.py",
    "src/nfl_forecast/props_integration.py",
    "scripts/run_props_research_beta.py",
)
_FIXED_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


class ReplayBundleError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json_bytes(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReplayBundleError(f"{path} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ReplayBundleError(f"{path} must contain a JSON object")
    return payload, raw


def _git_bytes(repo_root: Path, revision: str, path: str) -> bytes:
    revision = str(revision or "").strip()
    if len(revision) < 7:
        raise ReplayBundleError("generation_base_sha is missing or invalid")
    try:
        return subprocess.check_output(
            ["git", "show", f"{revision}:{path}"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as exc:
        raise ReplayBundleError(
            f"cannot read {path} at generation revision {revision}"
        ) from exc


def _resolve_manifest_path(root: Path, relative: object) -> Path:
    text = str(relative or "").strip()
    if not text:
        raise ReplayBundleError("manifest slate entry is missing manifest_file")
    candidate = (root / text).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ReplayBundleError("manifest path escapes manifest root") from exc
    return candidate


def _zip_member(name: str, data: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(name, date_time=_FIXED_ZIP_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    return info, data


def write_deterministic_archive(path: Path, members: Mapping[str, bytes]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(
        tmp,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name in sorted(members):
            info, data = _zip_member(name, members[name])
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    tmp.replace(path)
    return _sha256_bytes(path.read_bytes())


def build_replay_bundle(
    *,
    manifest_slate_path: Path,
    source_provenance_path: Path,
    output_dir: Path,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    slate, slate_raw = _load_json_bytes(manifest_slate_path)
    verify_manifest_slate_index(slate)

    provenance, _ = _load_json_bytes(source_provenance_path)
    generation_base_sha = str(provenance.get("generation_base_sha") or "").strip()
    source_workflow_run = str(provenance.get("source_workflow_run") or "").strip()
    live_run_id = str(provenance.get("live_run_id") or "").strip()
    if not generation_base_sha or not source_workflow_run or not live_run_id:
        raise ReplayBundleError(
            "source provenance requires generation_base_sha, source_workflow_run and live_run_id"
        )

    code_sha256 = {
        path: _sha256_bytes(_git_bytes(repo_root, generation_base_sha, path))
        for path in CODE_PATHS
    }

    root = manifest_slate_path.parent
    members: dict[str, bytes] = {"manifest_slate.json": slate_raw}
    games: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in slate["games"]:
        game_id = str(item.get("game_id") or "").strip()
        if not game_id or game_id in seen:
            raise ReplayBundleError(f"invalid or duplicate game_id: {game_id!r}")
        seen.add(game_id)

        manifest_path = _resolve_manifest_path(root, item.get("manifest_file"))
        manifest, raw = _load_json_bytes(manifest_path)
        verify_manifest_fingerprint(manifest)
        declared_sha = str(item.get("manifest_sha256") or "").strip()
        internal_sha = str(manifest.get("manifest_sha256") or "").strip()
        if declared_sha != internal_sha:
            raise ReplayBundleError(f"manifest fingerprint mismatch for {game_id}")
        if str(manifest.get("game_id") or "").strip() != game_id:
            raise ReplayBundleError(f"manifest game_id mismatch for {game_id}")

        member_name = f"games/{game_id}.manifest.json"
        members[member_name] = raw
        games.append(
            {
                "game_id": game_id,
                "archive_member": member_name,
                "manifest_sha256": internal_sha,
                "file_sha256": _sha256_bytes(raw),
                "seed": int(manifest.get("seed", 0)),
                "simulations": int(manifest.get("simulations", 20_000)),
                "model_version": str(
                    manifest.get("model_version") or "levline-props-simulation-v0.1.0"
                ),
                "prediction_interval_level": float(
                    manifest.get("prediction_interval_level", 0.80)
                ),
                "forecast_timestamp_utc": str(manifest.get("forecast_timestamp_utc") or ""),
                "kickoff_utc": str(manifest.get("kickoff_utc") or ""),
            }
        )

    if int(slate.get("game_count") or -1) != len(games):
        raise ReplayBundleError("replay game count disagrees with manifest slate")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / ARCHIVE_NAME
    archive_sha256 = write_deterministic_archive(archive_path, members)

    index = {
        "contract_version": CONTRACT_VERSION,
        "research_only": True,
        "production_authorized": False,
        "exact_replay_required": True,
        "source_workflow_run": source_workflow_run,
        "live_run_id": live_run_id,
        "generation_base_sha": generation_base_sha,
        "trigger_head_sha": provenance.get("trigger_head_sha"),
        "created_utc": provenance.get("created_utc"),
        "forecast_timestamp_utc": slate.get("forecast_timestamp_utc"),
        "game_count": len(games),
        "game_ids": [row["game_id"] for row in games],
        "manifest_slate_payload_sha256": payload_sha256(slate),
        "manifest_slate_file_sha256": _sha256_bytes(slate_raw),
        "archive_file": ARCHIVE_NAME,
        "archive_sha256": archive_sha256,
        "code_sha256": code_sha256,
        "games": games,
        "guardrail": (
            "Replay evidence only. Bundle construction does not alter Props forecasts, "
            "F-ST, winner probabilities, market capture, QA or signal classification."
        ),
    }
    (output_dir / INDEX_NAME).write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return index


def verify_replay_bundle(
    *,
    index_path: Path,
    archive_path: Path | None = None,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    index, _ = _load_json_bytes(index_path)
    if index.get("contract_version") != CONTRACT_VERSION:
        raise ReplayBundleError("unexpected replay bundle contract version")
    if not bool(index.get("research_only")) or bool(index.get("production_authorized")):
        raise ReplayBundleError("replay bundle governance flags are invalid")

    archive = archive_path or index_path.parent / str(index.get("archive_file") or "")
    if not archive.is_file():
        raise ReplayBundleError("replay archive is missing")
    if _sha256_bytes(archive.read_bytes()) != str(index.get("archive_sha256") or ""):
        raise ReplayBundleError("replay archive SHA-256 mismatch")

    generation_base_sha = str(index.get("generation_base_sha") or "")
    expected_code = index.get("code_sha256")
    if not isinstance(expected_code, dict):
        raise ReplayBundleError("replay index is missing code_sha256")
    for path in CODE_PATHS:
        expected = str(expected_code.get(path) or "")
        actual = _sha256_bytes(_git_bytes(repo_root, generation_base_sha, path))
        if expected != actual:
            raise ReplayBundleError(f"generation code fingerprint mismatch: {path}")

    with zipfile.ZipFile(archive, "r") as zf:
        names = zf.namelist()
        if names != sorted(names):
            raise ReplayBundleError("replay archive members are not canonically ordered")
        if "manifest_slate.json" not in names:
            raise ReplayBundleError("replay archive is missing manifest_slate.json")
        slate_raw = zf.read("manifest_slate.json")
        slate = json.loads(slate_raw)
        verify_manifest_slate_index(slate)
        if _sha256_bytes(slate_raw) != index.get("manifest_slate_file_sha256"):
            raise ReplayBundleError("manifest slate file SHA-256 mismatch")
        if payload_sha256(slate) != index.get("manifest_slate_payload_sha256"):
            raise ReplayBundleError("manifest slate payload SHA-256 mismatch")

        rows = index.get("games")
        if not isinstance(rows, list) or len(rows) != int(index.get("game_count") or -1):
            raise ReplayBundleError("replay index games are invalid")
        for row in rows:
            if not isinstance(row, dict):
                raise ReplayBundleError("replay game row must be an object")
            member = str(row.get("archive_member") or "")
            if member not in names:
                raise ReplayBundleError(f"missing replay manifest member: {member}")
            raw = zf.read(member)
            if _sha256_bytes(raw) != str(row.get("file_sha256") or ""):
                raise ReplayBundleError(f"manifest file SHA-256 mismatch: {member}")
            manifest = json.loads(raw)
            verify_manifest_fingerprint(manifest)
            if str(manifest.get("manifest_sha256") or "") != str(row.get("manifest_sha256") or ""):
                raise ReplayBundleError(f"manifest payload fingerprint mismatch: {member}")
            if str(manifest.get("game_id") or "") != str(row.get("game_id") or ""):
                raise ReplayBundleError(f"manifest game identity mismatch: {member}")

    return index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-slate", type=Path)
    parser.add_argument("--source-provenance", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-index", type=Path)
    parser.add_argument("--verify-archive", type=Path)
    args = parser.parse_args()

    if args.verify_index:
        verify_replay_bundle(
            index_path=args.verify_index,
            archive_path=args.verify_archive,
        )
        print(f"verified Props 2.2 replay bundle -> {args.verify_index}")
        return 0

    if not args.manifest_slate or not args.source_provenance or not args.output_dir:
        parser.error(
            "build mode requires --manifest-slate, --source-provenance and --output-dir"
        )
    index = build_replay_bundle(
        manifest_slate_path=args.manifest_slate,
        source_provenance_path=args.source_provenance,
        output_dir=args.output_dir,
    )
    print(
        f"built Props 2.2 replay bundle: games={index['game_count']} "
        f"archive_sha256={index['archive_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
