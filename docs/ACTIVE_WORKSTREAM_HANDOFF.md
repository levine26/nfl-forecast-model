# Active LevLine / Sunday Signal Workstream Handoff

**Point-in-time:** 2026-09-21 evening America/Los_Angeles  
**Repository:** `levine26/nfl-forecast-model`

This file is the cross-chat continuity source. Always re-check current `main`, open PRs, and current workflow runs before acting. Do not restart completed work or revive superseded PRs by default.

## Non-negotiable governance

- Do not modify the official LevLine/F-ST winner model while working Props/editorial research lanes.
- Do not weaken chronology, locking, research firewalls, immutable receipt rules, or launch gates to make CI pass.
- Frozen Props 2.1 Week 2 outcomes are evaluation/diagnostic evidence only. They may motivate hypotheses but may not fit coefficients, choose weights retrospectively, tune thresholds, or construct retrospective betting signals.
- Props 2.2 is future-holdout only. Week 2 receipts must never be backfilled into its prospective ledger.

## Sunday Signal — repaired state

The post-kickoff editorial collapse has been resolved.

Key merged fixes include:
- #450 canonical locked-slate bridge;
- #455 persisted weekend editorial roster;
- #456 challenger-output race isolation;
- #465 last launch-grade full-slate recovery;
- #476 docs-only recovery race allowance;
- #480 full ChatGPT-ingestion / failed-game-fallback namespace isolation;
- #483 isolated six-game fallback retry;
- #485 code-only full-ingestion pushes validate without republishing stale bundles.

Verified on committed `main` before this handoff:
- frozen Week 2 weekend roster: **15 games**;
- `outputs/copilot_media_reads.json`: **15 games**;
- editorial finalizer: **healthy, 15 games, 15 unique headlines**;
- provider: **healthy, 15/15 applied**;
- media reporting: **healthy, 15 trusted games**;
- Groq fallback state: **healthy**;
- all previously unresolved six games were recovered through validated ChatGPT fallback;
- `requires_chatgpt_refresh=true`: **zero**;
- recovery preserved a launch-grade historical editorial snapshot and did not alter LevLine/F-ST probabilities, picks, grading, or locks.

Do not reopen the prior one-game collapse investigation unless current committed artifacts regress.

## Props 2.1 — frozen evidence

Canonical prospective cohort:
- live workflow: `35477049179`;
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`;
- receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`;
- **3,439** frozen forecasts across **15 games**;
- retrospective forecast mutation: forbidden.

Canonical evaluation was merged in #466.

Observed Week 2 evaluation:
- **1,606** forecasts graded across 14 finalized games;
- **359** like-for-like market-matched forecasts;
- Fair-Line minus original-market MAE delta: about **+1.375**, game-clustered 95% CI roughly **[+0.828, +2.001]**;
- model-minus-market Brier delta: about **+0.0243**, CI roughly **[+0.0066, +0.0414]**;
- model-minus-market log-loss delta: about **+0.1035**, CI roughly **[+0.0432, +0.1729]**;
- preregistered probability bins showed systematic model overconfidence;
- zero original `MODEL EDGE` observations, therefore betting ROI is not measurable.

Interpretation: Week 2 did not show incremental accuracy beyond the point-in-time market. This is a diagnosis/development cohort, not a valid tuning/validation loop.

## Props engineering already merged

Do not redo:
- #434 — full eligible-roster concentration semantics;
- #446 — point-in-time depth-chart transport;
- #459 — fully-started target week becomes a clean live no-op;
- #478 — Props 2.2 market-residual future-holdout preregistration;
- #479 — locked Week 2 descriptive miss diagnostics;
- #481 — future Props 2.1 receipts preserve source distribution evidence;
- #482 — deterministic outcome-free Props 2.2 market-residual transformations;
- #485 — ChatGPT full-ingestion code-only pushes are validation-only no-ops.

### Frozen Props 2.2 design

The preregistered grid contains:
- `P21_BASE` control;
- line residual 25% / 50%;
- probability residual 25% / 50%;
- fixed probability shrink-to-half diagnostic;
- combined 25% / 50% primary challengers.

Only the two combined challengers are promotion eligible. Required terminal evidence includes at least 3 future weeks, 30 finalized games, 1,000 matched observations, clean chronology, and multiplicity control. The original point-in-time market remains the required comparator.

## Current active Props lanes

### #486 — immutable Props 2.2 prospective capture

Critical path.

Responsibilities:
- consume only outcome-free Props 2.1 prospective source rows;
- verify frozen baseline model identity;
- apply every frozen 2.2 challenger mechanically;
- immutable/idempotent JSONL capture keyed by source hash + challenger ID;
- conflicting duplicate identities fail closed;
- reject all source forecasts before **2026-09-22T02:25:08Z**, so Week 2 cannot be retrospectively backfilled;
- support the current-run `public_challenger.json` source so live integration never needs to scan the historical ledger.

Merge only after its focused capture test, preregistration gate, firewall, and integration checks are green.

### #489 — live Props 2.2 prospective capture hook

Stacked on #486.

After a successful pregame Props 2.1 build:
1. capture the just-generated current-run 2.1 JSON;
2. apply all frozen 2.2 candidates;
3. append to `challenger_outputs/props22/forecast_originals.jsonl`;
4. stage only research challenger outputs with the normal live Props artifact.

Post-kickoff no-op exits before capture. This lane must remain research-only and must never create production Props labels.

After #486 merges, retarget/rebuild #489 cleanly on current main if necessary.

### #487 — distribution-evidence evaluator

Forward-only evaluation infrastructure for evidence introduced by #481.

Continuous receipts preserve:
- standard deviation;
- prediction interval low/high/nominal coverage.

They do **not** preserve the lossless continuous simulation distribution. Therefore exact CRPS and PIT are explicitly unavailable and must not be fabricated.

The evaluator scores:
- interval coverage;
- interval width/sharpness;
- standardized absolute residual.

TD receipts preserve discrete TD count probabilities and can support:
- 1+ TD Brier/log loss;
- multiclass log loss when realized count is represented;
- ranked probability score when support is adequate.

### #488 — personnel/opportunity evidence coverage audit

Descriptive instrumentation only.

Measure future prospective coverage of:
- known role state;
- known availability state;
- known workload state;
- evidence IDs/provenance;
- opportunity state;
- pregame chronology.

Report by position and prop family. Do not use current coverage rates to retrospectively exclude subgroups or fit forecast weights.

## Dependency order

1. Land #486.
2. Retarget/land #489 on current main.
3. Land #487 and #488 when focused checks/firewall/integration are clean.
4. Before the next untouched pregame slate, verify the live Props workflow actually writes 2.2 receipts.
5. Preserve future 2.1 distribution evidence and personnel coverage concurrently.
6. Do not evaluate/select a 2.2 winner until the preregistered terminal evidence threshold is reached.

## Next-chat first actions

1. Read this file and `research/props/v21/CURRENT_STATE_AND_NEXT_STEPS.md`.
2. Check current open PRs; expected active scientific lanes are #486–#489 unless already merged/replaced.
3. Prioritize prospective capture readiness over retrospective Week 2 analysis.
4. Verify Sunday Signal remains 15/15 healthy, but do not let editorial maintenance block Props work if it remains healthy.
5. If any PR is stale/non-mergeable after main advances, create one clean current-main replacement and close the stale predecessor.
6. Never reuse Week 2 to choose a Props 2.2 coefficient, subgroup, or threshold.
