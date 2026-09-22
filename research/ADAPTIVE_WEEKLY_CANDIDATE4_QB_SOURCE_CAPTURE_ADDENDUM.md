# Candidate 4 QB source-contract capture hardening

Status: **PRE-FIRST-EXECUTION IMPLEMENTATION HARDENING — NO SCIENTIFIC RULE CHANGE**  
Date: 2026-09-22  
Parent contract: `ADAPTIVE-CANDIDATE4-QB-SHOCK-SOURCE-V1`  
Candidate preregistration: `74ecd303545c09f57593546472d27438e3d8a204`

## Purpose

The parent contract already freezes the T-120 QB1 identity source as timestamped nflverse depth-chart state with `dt <= T-120`. This addendum strengthens provenance by requiring the repository to **actually preserve the selected QB1 identity during the one-sided T-120 capture window**, instead of first querying the depth-chart dataset after T-60 and relying only on the upstream `dt` timestamp.

This is a stricter implementation of the existing source rule. It does not alter the Candidate 4 hypothesis, horizon, player identity definition, shock direction, thresholds, or winner rule.

## Frozen execution path

For each Candidate 4 primary-eligible Week 3+ Sunday game:

1. During `T-120 - 7.5 minutes <= capture_time <= T-120`, load the 2026 nflverse depth-chart surface through the pinned `nflreadpy` dependency.
2. Exclude any depth row whose `dt` is later than the actual repository capture timestamp.
3. Select the latest legal team snapshot and require exactly one rank-1 QB with non-empty `player_name` and `gsis_id`.
4. Preserve both teams' selected QB1 identities, source `dt` timestamps, actual repository capture timestamp, nflreadpy version, and a content hash in an append-only T-120 QB1 ledger.
5. The later T-60 QB-shock job may read only that frozen T-120 ledger. It may not re-query or re-derive depth-chart QB1 state.
6. Missing, late, ambiguous, or uncaptured T-120 QB1 state fails closed for that game and cannot be repaired retrospectively.

## Research firewall

- No game outcome or score is read by the T-120 capture.
- No player-value magnitude is estimated.
- No manual QB override is permitted.
- No production forecast is changed.
- Completed 2026 outcomes used for design or selection: **0**.
- First possible primary Candidate 4 cohort remains **Week 3 Sunday, September 27, 2026**.

This addendum strengthens point-in-time provenance only and does not create a new candidate clock.
