# LevLine Props — Current State and Next Steps

Updated: 2026-09-21 / 2026-09-22 UTC

This is the canonical Props-specific handoff. Do not restart the project or re-audit superseded branches unless current repository evidence requires it.

## Frozen Props 2.1 cohort

- source live workflow: `35477049179`
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
- receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`
- forecasts: **3,439**
- games: **15**
- players: **744**
- forecast week: **2026 Week 2**
- retrospective mutation: **forbidden**

Canonical evaluation was merged in PR #466.

## Week 2 prospective result

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

Do not tune or select a successor using Week 2 outcomes.

## Completed work

Merged and complete:
- #434 eligible-roster concentration semantics;
- #446 point-in-time depth-chart transport;
- #459 post-kickoff live no-op;
- #466 canonical prospective evaluation;
- #478 Props 2.2 future-holdout preregistration;
- #479 diagnostic Week 2 error decomposition;
- #481 forward distribution-evidence preservation in new 2.1 receipts;
- #482 deterministic Props 2.2 transformations.

## Frozen Props 2.2 research program

Baseline: `levline-props-2.1-sunday-v0.1`.

The frozen 2.2 grid includes:
- `P21_BASE`;
- line residual 25% / 50%;
- probability residual 25% / 50%;
- fixed 50% shrink-to-half probability diagnostic;
- combined 25% / 50% primary challengers.

Only `P22_COMBINED_25` and `P22_COMBINED_50` are promotion eligible.

No promotion/model-selection claim before:
- 3 future weeks;
- 30 finalized games;
- 1,000 matched observations;
- 250 observations for a prop-family superiority claim;
- clean chronology/receipt integrity;
- game-clustered uncertainty;
- Holm-Bonferroni control across the two promotion candidates;
- no material Brier/log-loss degradation.

## Active lanes

### #486 — prospective 2.2 capture contract

Highest priority.

- outcome-free sources only;
- frozen 2.1 baseline identity required;
- immutable source and challenger hashes;
- idempotent ledger append;
- conflicting duplicate identities fail closed;
- source timestamps before `2026-09-22T02:25:08Z` are rejected;
- supports current-run `public_challenger.json`, avoiding historical-ledger scans.

This time boundary prevents any Week 2 backfill after outcomes were observed.

### #489 — live prospective capture integration

Stacked on #486.

On a successful **pregame** live Props run:
- build Props 2.1;
- capture the just-generated current-run 2.1 JSON;
- apply every frozen 2.2 challenger;
- append immutable research receipts under `challenger_outputs/props22/`.

Fully-started weeks exit through the existing clean no-op before capture.

### #487 — distribution evidence evaluation

For future receipts created after #481:
- continuous: interval coverage, interval width, standardized residual;
- exact CRPS/PIT remain unavailable because the full continuous simulation distribution is not preserved;
- TD: 1+ TD Brier/log loss and supported discrete distribution scores.

Never describe an approximation as exact CRPS/PIT.

### #488 — personnel/opportunity coverage audit

Forward descriptive audit only:
- role known rate;
- availability known rate;
- workload known rate;
- evidence provenance coverage;
- opportunity-state coverage;
- chronology validity;
- grouped by position / prop family.

This lane measures data readiness; it does not fit a forecast rule.

## Scientific priority

The current question is no longer “how can Week 2 be made to look better?”

The forward questions are:
1. Does the preregistered 2.2 market-residual disagreement contain incremental information beyond the original market?
2. Does improved prospective personnel/opportunity evidence reduce UNKNOWN state and improve future challengers?
3. Are future uncertainty intervals/discrete TD distributions calibrated?
4. Can any improvement persist across multiple untouched weeks with valid chronology?

## Execution order

1. Merge #486 after focused capture/prereg/firewall/integration checks.
2. Retarget and merge #489 after #486.
3. Merge #487/#488 once focused checks and firewalls are clean.
4. Confirm the next pregame live run writes both 2.1 and 2.2 immutable receipts.
5. Do not select a 2.2 winner mid-holdout.
6. Run preregistered evaluation only after games finalize; keep per-week results descriptive until terminal thresholds are met.

## Repository hygiene

Do not reopen #447/#448/#457/#458, #468/#471/#474/#473, or other superseded experiments by default. Their useful work has already been consolidated into current main replacements.

If a current active PR becomes stale after main advances, create one clean current-main replacement, close the stale PR with an explicit supersession note, and continue.
