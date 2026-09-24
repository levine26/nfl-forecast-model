# PHASE 4 PRE-RESULT IMPLEMENTATION RECEIPT

Program: `LEVLINE_ATS_FRONTIER_V2`

Status: `PASS`

Date: `2026-09-24`

Branch: `research/ats-frontier-v2-phase4`

Validated scientific head: `c1eead294c5ac897041fc35f628b2fec393ab064`

Pre-result workflow: `ATS Frontier V2 Phase 4 pre-result gate`

Workflow run ID: `36025017029`

Job ID: `107719216108`

Conclusion: `success`

Accepted execution concurrency identity: `ats-frontier-v2-phase4-accepted-v2`

Candidate performance accepted before this receipt: `NO`

Completed-2026 outcomes used: `0`

Production forecasting surfaces changed: `NO`

Superseded execution run: `36023376614` — `INVALID / NOT ACCEPTED`; see `PHASE4_INVALID_RUNS.md`.

## Frozen corrected implementation identity

The exact accepted pre-result scientific implementation is the Git tree at validated head `c1eead294c5ac897041fc35f628b2fec393ab064`, specifically:

- `research/ats-frontier-v2/phase4_config.json`
- `research/ats-frontier-v2/phase4_core.py`
- `research/ats-frontier-v2/phase4_runner.py`
- `research/ats-frontier-v2/phase4_accepted_runner.py`
- `research/ats-frontier-v2/test_phase4.py`
- `research/ats-frontier-v2/test_phase4_acceptance.py`
- `.github/workflows/research_ats_frontier_v2_phase4_gate.yml`

The corrected acceptance surface preserves the frozen candidates, features, state dimensions, grids, distributions, key numbers, market horizon, targets, and selection rules. It corrects only contract-compliance/engineering details discovered before accepting evidence:

1. `STATIC_FOOTBALL_STATE` now uses the preregistered prior-only exponentially pooled baseline, fixed to the repository-consistent 8-game EWMA half-life with no result-driven tuning;
2. M3 state history may update from every completed prior regular-season football game even where the historical market benchmark is absent; exact market-row filtering remains confined to fitting/scoring comparisons;
3. M4 emits the required ranked-probability, margin-error, and tail diagnostics without changing its fitted probability law or primary score.

Frozen deterministic bootstrap seed: `20260924`.

## Corrected result-blind gate evidence

Every required pre-result step passed at the validated head:

1. repository checkout: PASS
2. Python/dependency setup: PASS
3. compile complete Phase-4 research surface: PASS
4. original synthetic/preregistered contract tests: PASS
5. corrected acceptance-surface tests: PASS
6. corrected result-blind preflight receipt: PASS
7. completed-2026 loader firewall proof: PASS
8. protected production-surface diff: PASS

## Synthetic contracts proven before accepted target scoring

- canonical home-margin sign convention;
- ATS cover/push/loss grading;
- M3 scalar Gaussian state update;
- M3 season transition;
- predict-all-then-update-all week chronology;
- prior-QB identity only, with league prior for unknown QBs;
- target-week observations cannot enter target-week predictors;
- static ablation is fixed prior-only EWMA rather than expanding mean;
- state-history construction is not conditioned on availability of a target market benchmark row;
- M4 analytic full-lattice normalization;
- M4 nonnegative/finite probabilities;
- M4 whole-number structural push mapping;
- M4 half-point push probability equals zero;
- M4 sign reversal symmetry;
- M4 extreme-input finite behavior;
- no finite-support endpoint folding;
- completed-2026 outcomes excluded by loader construction;
- production surfaces unchanged from the research branch base.

## Scientific freeze after this receipt

Historical scoring eligible for acceptance is permitted only from the corrected validated scientific head above, plus non-scientific receipt/evidence-preservation commits that leave the frozen scientific surfaces unchanged. Any later engineering correction must preserve the frozen hypotheses and invalidate the affected run before replacement. No feature, hyperparameter, state dimension, distribution, key number, calibration method, subset, selective threshold, rescue candidate, M1/M2 historical experiment, or M3+M4 composition may be added after performance inspection.

This receipt closes the corrected pre-result gate. It contains no accepted Phase-4 performance result.
