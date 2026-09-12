from __future__ import annotations

"""Audit main-branch advances that occur while Groq researches a slate.

Groq paragraph-one research is reusable when only deterministic forecast/diagnostic
outputs advance. It is not reusable when the contextual inputs used to build the
research packet, the provider artifact itself, or repository code/configuration
changes underneath the run.
"""

import sys
from dataclasses import dataclass
from typing import Iterable


RESEARCH_SENSITIVE_OUTPUTS = frozenset(
    {
        "outputs/contextual_evidence.json",
        "outputs/game_previews.json",
        "outputs/context_source_status.json",
        "outputs/copilot_media_reads.json",
    }
)


@dataclass(frozen=True)
class MainAdvanceAudit:
    changed: tuple[str, ...]
    research_sensitive: tuple[str, ...]
    non_output: tuple[str, ...]

    @property
    def safe_to_reconcile(self) -> bool:
        return not self.research_sensitive and not self.non_output


def audit_main_advance(paths: Iterable[str]) -> MainAdvanceAudit:
    changed = tuple(sorted({str(path).strip() for path in paths if str(path).strip()}))
    research_sensitive = tuple(path for path in changed if path in RESEARCH_SENSITIVE_OUTPUTS)
    non_output = tuple(path for path in changed if not path.startswith("outputs/"))
    return MainAdvanceAudit(
        changed=changed,
        research_sensitive=research_sensitive,
        non_output=non_output,
    )


def main() -> int:
    audit = audit_main_advance(sys.stdin.read().splitlines())
    if audit.research_sensitive:
        print("Main advanced in Groq research/publication inputs; refusing stale research:", file=sys.stderr)
        for path in audit.research_sensitive:
            print(path, file=sys.stderr)
    if audit.non_output:
        print("Main advanced outside deterministic outputs; refusing stale research:", file=sys.stderr)
        for path in audit.non_output:
            print(path, file=sys.stderr)
    if not audit.safe_to_reconcile:
        return 1

    print(f"Reconcilable deterministic-output advance: {len(audit.changed)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
