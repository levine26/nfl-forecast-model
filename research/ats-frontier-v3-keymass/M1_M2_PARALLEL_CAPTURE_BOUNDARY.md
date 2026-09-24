# M1 / M2 Parallel Capture Boundary

Existing identities remain separate: `FV2-PROS-M1-MARKETSTATE-01` and `FV2-PROS-M2-QBDELTA-01`. They are never features of or merged with V3.

## M1 — active governed market capture
Preserve the existing scheduled research-only market collector: sportsbook, spread, side price, moneyline, total, provider quote time, ingestion/request time, kickoff, and raw payload/hash across its governed horizons, including T-120. `.github/workflows/research_market_capture_v2.yml` remains the authoritative live capture path. V3 does not change its contract or evaluate M1 outcomes.

## M2 — partial active prospective capture, no synthesis
The repository already contains a scheduled five-minute `Adaptive Candidate 4 T-120 QB1 snapshot` workflow that persists immutable T-120 QB1 identities to the research-data branch, plus the governed Candidate-4 QB-shock information-state capture chained from the inactive-article archive. Preserve those collectors and their timestamps. They constitute legitimate prospective evidence where their own contracts qualify the source.

This does **not** certify complete M2 coverage of announced starter, practice status, injury designation, expected-starter probability inputs, depth-chart changes, and every update timestamp. Other availability/depth-chart workflows are research audits or source-validation lanes and must not be relabeled as complete live M2 capture without their own authorization. Missing prospective fields remain missing; no retrospective synthesis after outcomes is permitted.

M1/M2 outcome evaluation is not authorized by V3, and neither lane may feed `FV3-PROS-KMASS-01`.
