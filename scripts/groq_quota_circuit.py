from __future__ import annotations

"""Classify shared Groq long-window quota exhaustion without exposing response text.

This scanner is only applied to provider stderr from the current game, never to
article text or untrusted editorial payloads. The full input is not published.
"""

import argparse
from pathlib import Path
import re

_QUOTA = re.compile(
    r"\bGroq HTTP 429\b[^\n]{0,250}\bclass\s*=\s*([a-z0-9_,\-]+)",
    flags=re.I,
)
_GLOBAL = frozenset({"tpd", "rpd"})


def shared_long_window_quota_exhausted(log_text: str) -> bool:
    """Only daily token/request exhaustion stops other independent games."""
    for match in _QUOTA.finditer(str(log_text or "")):
        codes = {part.strip().lower() for part in match.group(1).split(",")}
        if codes & _GLOBAL:
            return True
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="Private Groq 429 quota classifier")
    p.add_argument("--stderr-file", type=Path, required=True)
    args = p.parse_args()
    try:
        raw = args.stderr_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 1
    return 0 if shared_long_window_quota_exhausted(raw) else 1


if __name__ == "__main__":
    raise SystemExit(main())
