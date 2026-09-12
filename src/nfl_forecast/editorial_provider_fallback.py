from __future__ import annotations

"""Per-game editorial fallback recovery for Sunday Signal.

Groq is the primary autonomous writer. A Groq transport or focused-validation failure
must affect only that matchup, never erase successful Groq work for the rest of the
slate. This module recovers one failed game from a fresh ChatGPT safety bundle when
available, otherwise from the last already-validated provider artifact. Every recovered
payload still passes the existing focused and full-slate validators before publication.

This module is editorial-only. It never reads or writes model coefficients, probability
inputs, locks, grading state, or market data.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

CHATGPT_MAX_AGE_HOURS = 4.0
CHATGPT_PRODUCER = "chatgpt-consumer-session"
CHATGPT_RESEARCH_MODE = "live-web-search"
CHATGPT_FORECAST_PATH = "F-ST-01-FROZEN-2026"
PROVIDER_STATUS_POLICY = (
    "Groq failures are game-specific; successful Groq games remain authoritative and "
    "failed games use validated ChatGPT/last-good editorial fallback."
)


def _utc(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_reason(value: Any) -> str:
    text = _clean(value)
    text = re.sub(r"[^a-zA-Z0-9_.:,= /-]+", "", text)
    return text[:240] or "provider_failure"


def _fresh_chatgpt_payload(chatgpt_dir: Path, game_id: str, now: datetime) -> Path | None:
    manifest_path = chatgpt_dir / "manifest.json"
    payload_path = chatgpt_dir / f"{game_id}.json"
    if not manifest_path.is_file() or not payload_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(manifest, dict):
        return None
    if manifest.get("producer") != CHATGPT_PRODUCER:
        return None
    if manifest.get("research_mode") != CHATGPT_RESEARCH_MODE:
        return None
    if manifest.get("forecast_path_identity") != CHATGPT_FORECAST_PATH:
        return None
    games = manifest.get("game_ids")
    if not isinstance(games, list) or game_id not in {str(value) for value in games}:
        return None
    generated = _utc(manifest.get("generated_utc"))
    if generated is None:
        return None
    age_hours = (now - generated).total_seconds() / 3600.0
    if age_hours < -0.1 or age_hours > CHATGPT_MAX_AGE_HOURS:
        return None
    return payload_path


def _qualitative_rationale(entry: dict[str, Any]) -> str:
    direct = _clean(entry.get("model_rationale"))
    prohibited = re.compile(
        r"\d|%|\blevline\b|\bf-st\b|\bpure\b|\bmarket\b|\bspread\b|\bmodel line\b|\bmoneyline\b",
        flags=re.I,
    )
    words = re.findall(r"\b[\w'-]+\b", direct)
    if 18 <= len(words) <= 40 and not prohibited.search(direct):
        return direct

    paragraph2 = _clean(entry.get("paragraph2"))
    without_pick = re.sub(r"\s*The pick:.*$", "", paragraph2, flags=re.I).strip()
    for sentence in reversed(re.split(r"(?<=[.!?])\s+", without_pick)):
        candidate = _clean(sentence)
        words = re.findall(r"\b[\w'-]+\b", candidate)
        if 18 <= len(words) <= 40 and not prohibited.search(candidate):
            return candidate
    # The focused validator is permitted to reconstruct an underlength rationale from
    # a recognized football mechanism in paragraph 1. Empty is therefore safer than
    # inventing new unsupported copy here.
    return ""


def _provider_artifact_text(provider_artifact: Path) -> str | None:
    """Read last-good editorial even if the workflow cleared the working file.

    The Groq workflow intentionally removes outputs/copilot_media_reads.json before it
    builds a new slate. The previously committed file is still available in Git HEAD,
    so an isolated provider failure can recover that validated game without weakening
    the workflow's clean-slate semantics.
    """
    if provider_artifact.is_file():
        try:
            return provider_artifact.read_text(encoding="utf-8")
        except Exception:
            return None
    if provider_artifact.is_absolute():
        return None
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{provider_artifact.as_posix()}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    return result.stdout if result.returncode == 0 and result.stdout.strip() else None


def _last_validated_payload(provider_artifact: Path, game_id: str) -> dict[str, Any] | None:
    raw = _provider_artifact_text(provider_artifact)
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    games = payload.get("games") if isinstance(payload, dict) else None
    entry = games.get(game_id) if isinstance(games, dict) else None
    if not isinstance(entry, dict):
        return None
    headline = _clean(entry.get("headline"))
    paragraph1 = _clean(entry.get("paragraph1"))
    sources = entry.get("sources")
    if not headline or not paragraph1 or not isinstance(sources, list) or not sources:
        return None
    return {
        "games": {
            game_id: {
                "headline": headline,
                "paragraph1": paragraph1,
                "model_rationale": _qualitative_rationale(entry),
                "sources": sources,
            }
        }
    }


def _run_id() -> str:
    return str(os.environ.get("GITHUB_RUN_ID") or "local").strip() or "local"


def _ephemeral_status_enabled() -> bool:
    """Use runner-local status only for real non-PR Groq production jobs.

    PR validation uses the same `write-media` job name but must not leak test state
    between cases. Other workflows can call the finalizer without being part of a Groq
    provider run, so they should also ignore this ephemeral ledger.
    """
    return (
        bool(os.environ.get("GITHUB_RUN_ID"))
        and os.environ.get("GITHUB_JOB") == "write-media"
        and os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
    )


def _ephemeral_status_path(run_id: str | None = None) -> Path:
    rid = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(run_id or _run_id()))
    return Path("/tmp") / f"sunday-signal-groq-provider-status-{rid}.json"


def _new_provider_section(run_id: str, now: datetime) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "status": "healthy",
        "games": {},
        "failed_games": [],
        "started_at_utc": now.astimezone(timezone.utc).isoformat(),
        "policy": PROVIDER_STATUS_POLICY,
    }


def _recompute_provider_section(section: dict[str, Any]) -> dict[str, Any]:
    games = section.get("games")
    if not isinstance(games, dict):
        games = {}
        section["games"] = games
    section["failed_games"] = sorted(
        gid
        for gid, item in games.items()
        if isinstance(item, dict) and item.get("provider_result") == "failed"
    )
    section["status"] = (
        "degraded"
        if any(
            bool(item.get("requires_chatgpt_refresh"))
            for item in games.values()
            if isinstance(item, dict)
        )
        else "healthy"
    )
    section["policy"] = PROVIDER_STATUS_POLICY
    return section


def _load_ephemeral_provider_section(now: datetime) -> tuple[Path, dict[str, Any]]:
    run_id = _run_id()
    path = _ephemeral_status_path(run_id)
    section: dict[str, Any] | None = None
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and str(loaded.get("run_id")) == run_id:
                section = loaded
        except Exception:
            section = None
    if section is None:
        section = _new_provider_section(run_id, now)
    return path, section


def _write_ephemeral_provider_section(section: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(_recompute_provider_section(section), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record_provider_success(game_id: str, *, now: datetime | None = None) -> None:
    """Record a successful current-run Groq game in runner-local state.

    The first game of a new run creates a fresh ledger, which also prevents a prior
    run's `requires_chatgpt_refresh` flags from leaking into a later all-success run.
    """
    if not _ephemeral_status_enabled():
        return
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    path, section = _load_ephemeral_provider_section(current)
    games = section.setdefault("games", {})
    games[str(game_id)] = {
        "provider": "groq",
        "provider_result": "success",
        "fallback_source": None,
        "requires_chatgpt_refresh": False,
        "completed_at_utc": current.isoformat(),
    }
    _write_ephemeral_provider_section(section, path)


def _record_ephemeral_fallback(*, game_id: str, reason: str, source: str, now: datetime) -> None:
    if not _ephemeral_status_enabled():
        return
    path, section = _load_ephemeral_provider_section(now)
    games = section.setdefault("games", {})
    games[str(game_id)] = {
        "provider": "groq",
        "provider_result": "failed",
        "fallback_source": source,
        "reason": _safe_reason(reason),
        "recovered_at_utc": now.isoformat(),
        "requires_chatgpt_refresh": source != "chatgpt",
    }
    _write_ephemeral_provider_section(section, path)


def merge_current_run_provider_status(status: dict[str, Any]) -> dict[str, Any]:
    """Restore runner-local provider status after any hard reset to latest main.

    `/tmp` survives the workflow's `git reset --hard origin/main`. The finalizer calls
    this function only in the Groq production job, replacing any stale previous-run
    fallback section with the current run's authoritative per-game ledger.
    """
    if not _ephemeral_status_enabled():
        return status
    path = _ephemeral_status_path()
    if not path.is_file():
        return status
    try:
        section = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return status
    if not isinstance(section, dict) or str(section.get("run_id")) != _run_id():
        return status
    merged = deepcopy(status)
    merged["groq_provider_fallback"] = _recompute_provider_section(section)
    return merged


def _record_fallback(
    *,
    game_id: str,
    reason: str,
    source: str,
    status_path: Path,
    now: datetime,
) -> None:
    status: dict[str, Any] = {}
    if status_path.is_file():
        try:
            loaded = json.loads(status_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                status = loaded
        except Exception:
            status = {}

    run_id = _run_id()
    section = status.get("groq_provider_fallback")
    if not isinstance(section, dict) or str(section.get("run_id")) != run_id:
        section = _new_provider_section(run_id, now)
    games = section.setdefault("games", {})
    games[game_id] = {
        "provider": "groq",
        "provider_result": "failed",
        "fallback_source": source,
        "reason": _safe_reason(reason),
        "recovered_at_utc": now.isoformat(),
        "requires_chatgpt_refresh": source != "chatgpt",
    }
    status["groq_provider_fallback"] = _recompute_provider_section(section)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _record_ephemeral_fallback(game_id=game_id, reason=reason, source=source, now=now)


def recover_focused_payload(
    *,
    game_id: str,
    output_path: str | Path,
    reason: str,
    chatgpt_dir: str | Path = "inputs/chatgpt_media/current",
    provider_artifact: str | Path = "outputs/copilot_media_reads.json",
    status_path: str | Path = "outputs/context_source_status.json",
    now: datetime | None = None,
) -> tuple[bool, str]:
    """Recover one focused payload and record why Groq failed for this game.

    Fresh ChatGPT research is preferred. If it is unavailable, the last full-slate
    artifact that already passed the publication validator is used only as an emergency
    continuity bridge; the status explicitly asks Sunday Signal Check for a fresh
    ChatGPT replacement.
    """
    gid = str(game_id)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    chatgpt_path = _fresh_chatgpt_payload(Path(chatgpt_dir), gid, current)
    if chatgpt_path is not None:
        output.write_text(chatgpt_path.read_text(encoding="utf-8"), encoding="utf-8")
        _record_fallback(
            game_id=gid,
            reason=reason,
            source="chatgpt",
            status_path=Path(status_path),
            now=current,
        )
        return True, "chatgpt"

    fallback = _last_validated_payload(Path(provider_artifact), gid)
    if fallback is not None:
        output.write_text(json.dumps(fallback, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        _record_fallback(
            game_id=gid,
            reason=reason,
            source="last_validated_editorial",
            status_path=Path(status_path),
            now=current,
        )
        return True, "last_validated_editorial"

    _record_fallback(
        game_id=gid,
        reason=reason,
        source="missing",
        status_path=Path(status_path),
        now=current,
    )
    return False, "missing"