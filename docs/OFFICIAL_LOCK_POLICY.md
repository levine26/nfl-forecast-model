# Official forecast lock policy (effective 2026 Week 6)

## Policy
- **2026 NFL Weeks 1–5, and all prior seasons:** official lock target **120 minutes before kickoff**.
- **2026 NFL Week 6 and later:** official lock target **60 minutes before kickoff**.
- Both targets permit up to 10 minutes of *operational lateness* before the alert/ontime SLO fails; the original actual timestamp is always recorded. A late-but-prekickoff official row is not called on-time.
- The target is based on canonical season/week and kickoff, **not** when a record was written, so 2026 Week 5 history can never be reclassified as on-time by switching policies.
- The same frozen production F-ST artifact and production scoring inputs are used. A changed lock horizon can change which *market snapshot* enters a locked official prediction; thus mixed-horizon accuracy must be reported by cohort rather than silently pooled as one homogeneous experiment.
- Historic official CSV receipts and research prospective shadow artifacts are never rewritten, moved, backdated, or reinterpreted.
- Independent research T-120 captures and preregistration remain unchanged. They are a separate research process, not the authority for official Week 6+ locks.

## Operational execution
- The canonical publisher and the lightweight append-only backup both enforce the policy per game, not a universal 120-minute window.
- The backup freshness gate may refresh the frozen F-ST production snapshot when the **due** game's cache is stale; it cannot override the 90-minute freshness rule or restore a missed on-time receipt.
- The fast-lock gate starts at approximately T-63 from Week 6; the full pregame model refresh may start earlier for compute latency.
- Public countdowns use the same year/week cutoff and always defer to actual immutable lock receipts.
- The read-only historic audit records each target and actual lateness. Mixed-year reports expose both target horizons rather than mislabeling a single policy.
- A missed GitHub cron trigger remains possible. Independent off-GitHub scheduling and alerting is tracked in [issue #701](https://github.com/levine26/nfl-forecast-model/issues/701), and is not solved solely by moving to T-60.

## Rollout and scientific guardrails
Any live Week 5 rows retain the original T-120 requirement, even if they were locked late. Week 6+ must demonstrate prospectively successful on-time locks and publication before reliability can be described as resolved. Maintain separate accuracy / ATS / calibration metrics for the pre-change and post-change cohorts. Do not promote a new model, alter frozen weights or rerecord historical results in response to this policy change.
