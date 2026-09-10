# Consolidated Copilot source-hardening cleanup

This branch replaces stale/conflicting PRs #56 and #58 with a clean implementation based on current `main`.

Included:
- centralized direct-report URL classification;
- official-team domain mapping;
- X/Twitter publisher-family normalization;
- fail-closed source backfill that accepts only URLs passing the strict direct-report classifier;
- deterministic matchup-specific LevLine prose to avoid accidental cross-game template collisions;
- standardized factual/status-language exemptions that preserve substantive editorial uniqueness checks;
- direct-report, backfill, uniqueness and source-family regressions.

Explicitly excluded:
- LevLine model inputs/features/probabilities;
- PURE/MARKET weights;
- T-120 locking or grading;
- challenger model code;
- site code;
- generated forecast outputs.
