# LevLine Props — Current State and Next Steps

Updated: 2026-09-21 / 2026-09-22 UTC

This is the canonical Props-specific handoff. Do not restart the project or re-audit superseded branches unless current repository evidence requires it.

## 1. Frozen Props 2.1 cohort

- source live workflow: `35477049179`
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
- receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`
- forecasts: **3,439**
- games: **15**
- players: **744**
- forecast week: **2026 Week 2**
- retrospective mutation: **forbidden**

Canonical evaluation is merged in PR #466.

## 2. Week 2 prospective result

At the evaluation point:
- **1,606** forecasts graded;
- **14** finalized games;
- **359** like-for-like market-matched forecasts.

Matched projection evidence:
- model-mean MAE: **11.770**
- Fair Line MAE: **11.983**
- original market-line MAE: **10.609**
- Fair-Line minus market paired MAE delta: **+1.375**
- game-clustered 95% CI: **[+0.828, +2.001]**

Matched probability evidence:
- model Brier: **0.2707**
- market Brier: **0.2465**
- delta: **+0.0243**, CI **[+0.0066, +0.0414]**
- model log loss: **0.7895**
- market log loss: **0.6860**
- delta: **+0.1035**, CI **[+0.0432, +0.1729]**

Calibration:
- every preregistered probability bin overpredicted realized hit rate;
- ECE: **0.1691**.

Other constraints:
- zero original `MODEL EDGE` observations -> ROI is not measurable;
- Week 2 continuous receipts did not preserve a lossless distribution -> exact CRPS/PIT unavailable;
- many Week 2 receipts had UNKNOWN personnel/workload state.

Scientific interpretation:
- Week 2 did **not** show incremental accuracy beyond the contemporaneous market;
- Week 2 is a locked diagnosis/development cohort;
- Week 2 outcomes may motivate hypotheses but may not select coefficients, weights, thresholds, subgroups, or betting rules;
- any successor changed because of Week 2 must be validated on future untouched data.

## 3. Completed engineering and research

Merged and complete:

- #434 — eligible-roster concentration semantics;
- #446 — point-in-time depth-chart transport;
- #459 — post-kickoff live no-op;
- #466 — canonical prospective evaluation;
- #478 — Props 2.2 future-holdout preregistration;
- #479 — descriptive Week 2 miss diagnostics without tuning;
- #481 — future source distribution/interval evidence preservation in 2.1 receipts;
- #482 — deterministic outcome-free Props 2.2 transformations;
- #486 — immutable Props 2.2 prospective capture contract;
- #487 — forward distribution-evidence scoring;
- #488 — future personnel/opportunity evidence coverage audit;
- #491 — live pregame integration for Props 2.2 receipt capture.

Do not redo these unless repository evidence shows they are broken.

## 4. Frozen Props 2.2 research program

Baseline: `levline-props-2.1-sunday-v0.1`.

Frozen grid:
- `P21_BASE`;
- line residual 25%;
- line residual 50%;
- probability residual 25%;
- probability residual 50%;
- fixed shrink-to-half probability diagnostic;
- combined 25% primary challenger;
- combined 50% primary challenger.

Only the combined challengers are promotion eligible.

No promotion/model-selection claim before:
- 3 future weeks;
- 30 finalized games;
- 1,000 matched observations;
- 250 observations for a prop-family superiority claim;
- clean chronology and receipt integrity;
- game-clustered uncertainty;
- Holm-Bonferroni control across promotion candidates;
- no material Brier/log-loss degradation.

The original point-in-time market remains the required comparator.

## 5. Props 2.2 prospective capture status

The capture code is merged and wired into the live Props workflow.

However, **no Props 2.2 ledger exists yet under `challenger_outputs/props22/` on committed main**.

That is expected and correct:
- #491 merged only after Week 2 had fully started;
- subsequent live Props runs have taken the governed post-kickoff no-op path;
- a no-op source run must not create prospective receipts;
- the capture contract rejects source forecasts earlier than the frozen 2.2 prospective start boundary, preventing Week 2 backfill.

The first future successful **pregame** live Props run is the acceptance event.

Required acceptance evidence:
1. a valid current-run Props 2.1 challenger artifact exists;
2. exact source live-run ID, generation SHA, trigger SHA, forecast timestamp, market timestamp/provider, and source hash are preserved;
3. every frozen Props 2.2 challenger is applied mechanically;
4. immutable/idempotent records are appended under `challenger_outputs/props22/`;
5. conflicting duplicate identities fail closed;
6. no target outcomes or grading fields are present;
7. production Props labels remain unchanged;
8. the LevLine/F-ST winner model remains untouched.

Do not manually create or backfill a Props 2.2 ledger from Week 2.

## 6. Forward evidence lanes already available

### Distribution evidence

Future receipts now preserve forward uncertainty evidence sufficient for:
- interval coverage;
- interval width/sharpness;
- standardized residual;
- TD 1+ Brier/log loss;
- supported discrete TD distribution scoring.

Do not fabricate exact CRPS or PIT when a lossless continuous simulation distribution was not preserved.

### Personnel/opportunity evidence

The merged audit measures future coverage of:
- role state;
- availability state;
- workload state;
- evidence/provenance IDs;
- opportunity state;
- chronology validity;
- grouped by position and prop family.

This is descriptive instrumentation. Do not use current coverage rates to retrospectively choose exclusions or fit forecast weights.

## 7. Completed lifecycle cleanup: PR #492

PR #492 is merged and complete.

Why it exists:
- the live Props workflow now correctly emits a successful post-kickoff no-op when no pregame games remain;
- four legacy Props 2.0 listeners still treated every successful source run as a full pregame capture;
- they therefore failed on a valid no-op artifact.

#492 should make those listeners:
- accept exactly one `levline-props-postkickoff-noop-v0.1` file as a clean skip;
- require zero pregame game IDs and at least one started game;
- skip all receipt/archive persistence on no-op;
- preserve all existing full-artifact provenance/SHA validation;
- fail closed for mixed/malformed artifacts.

These false-red workflows are infrastructure noise, not evidence of a forecasting-model failure.

## 8. Scientific priority from here

The question is not “how can Week 2 be made to look better?”

The forward questions are:

1. Do preregistered Props 2.2 market-residual challengers add incremental information beyond the original market on future untouched weeks?
2. Does improved prospective personnel/opportunity evidence reduce UNKNOWN state and improve future challenger accuracy?
3. Are future intervals and discrete TD distributions calibrated?
4. Can any improvement persist across multiple future weeks and games with valid chronology?
5. Do genuine original `MODEL EDGE` observations emerge prospectively, making betting-performance evaluation measurable?

## 9. Execution order

1. Before the next untouched pregame slate, verify the live Props workflow and #491 capture hook remain intact.
2. On the next successful pregame live run, verify the first immutable Props 2.2 ledger is created.
3. Run forward distribution and personnel/opportunity audits concurrently.
4. Do not select a Props 2.2 winner mid-holdout.
5. After future games finalize, run the frozen evaluator without changing candidate definitions.
6. Keep weekly findings descriptive until terminal evidence thresholds are met.

## 10. Repository hygiene

Do not reopen old Props 2.0 / 2.1 experimental PRs by default. Their useful work has been consolidated into current main.

If a current PR becomes stale after main advances, create one clean current-main replacement, close the stale predecessor with an explicit supersession note, and continue.

The active scientific chain is:

**Props 2.1 frozen baseline -> Props 2.2 preregistered challenger grid -> future untouched pregame receipts -> terminal paired evaluation vs original market.**
