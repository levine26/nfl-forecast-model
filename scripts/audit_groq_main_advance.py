from __future__ import annotations

"""Audit main-branch advances that occur while Groq researches a slate.

Groq paragraph-one research is reusable when only deterministic forecast/diagnostic
outputs or explicitly isolated research-only namespaces advance. It is not reusable
when the contextual inputs used to build the research packet, the provider artifact
itself, production/editorial code, or unknown repository configuration changes
underneath the run.
"""

import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


RESEARCH_SENSITIVE_OUTPUTS = frozenset(
    {
        "outputs/contextual_evidence.json",
        "outputs/game_previews.json",
        "outputs/context_source_status.json",
        "outputs/copilot_media_reads.json",
    }
)

# These namespaces are deliberately isolated from the production forecast/editorial
# path. Research is merged frequently while the Groq writer is running, so treating
# these files as production inputs creates false stale-research failures. Keep this
# list narrow: generic workflows/scripts/tests remain fail-closed below.
RESEARCH_ONLY_PREFIXES = (
    "research/",
    "docs/levline4/",
)


def is_research_only_path(path: str) -> bool:
    value = str(path or "").strip()
    if not value:
        return False
    if any(value.startswith(prefix) for prefix in RESEARCH_ONLY_PREFIXES):
        return True

    posix = PurePosixPath(value)
    parent = posix.parent.as_posix()
    name = posix.name
    if parent == ".github/workflows" and name.startswith("research_") and posix.suffix in {".yml", ".yaml"}:
        return True
    if parent == "scripts" and name.startswith("run_research_") and posix.suffix == ".py":
        return True
    if parent == "tests" and name.startswith("test_research_") and posix.suffix == ".py":
        return True
    return False


@dataclass(frozen=True)
class MainAdvanceAudit:
    changed: tuple[str, ...]
    research_sensitive: tuple[str, ...]
    research_only: tuple[str, ...]
    non_output: tuple[str, ...]

    @property
    def safe_to_reconcile(self) -> bool:
        return not self.research_sensitive and not self.non_output


def audit_main_advance(paths: Iterable[str]) -> MainAdvanceAudit:
    changed = tuple(sorted({str(path).strip() for path in paths if str(path).strip()}))
    research_sensitive = tuple(path for path in changed if path in RESEARCH_SENSITIVE_OUTPUTS)
    research_only = tuple(path for path in changed if is_research_only_path(path))
    research_only_set = set(research_only)
    non_output = tuple(
        path
        for path in changed
        if not path.startswith("outputs/") and path not in research_only_set
    )
    return MainAdvanceAudit(
        changed=changed,
        research_sensitive=research_sensitive,
        research_only=research_only,
        non_output=non_output,
    )


def main() -> int:
    audit = audit_main_advance(sys.stdin.read().splitlines())
    if audit.research_sensitive:
        print("Main advanced in Groq research/publication inputs; refusing stale research:", file=sys.stderr)
        for path in audit.research_sensitive:
            print(path, file=sys.stderr)
    if audit.non_output:
        print("Main advanced outside reconcilable outputs/research-only namespaces; refusing stale research:", file=sys.stderr)
        for path in audit.non_output:
            print(path, file=sys.stderr)
    if not audit.safe_to_reconcile:
        return 1

    if audit.research_only:
        print(f"Ignoring {len(audit.research_only)} isolated research-only main advance(s):")
        for path in audit.research_only:
            print(path)
    print(f"Reconcilable main advance: {len(audit.changed)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
