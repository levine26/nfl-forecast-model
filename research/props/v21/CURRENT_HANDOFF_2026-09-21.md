# LevLine Props 2.1 — Current Handoff (2026-09-21/22)

## Canonical current path

Use PR #458 / branch `research/props21-prospective-evaluation-current` as the canonical Props 2.1 prospective-evaluation lane. PRs #447, #448, and #457 are superseded/closed.

The production winner model and F-ST remain frozen and must not be changed by Props research.

## Live engineering state already merged

- PR #434 merged: full eligible roster concentration semantics.
- PR #445 merged: structured official availability.
- PR #446 merged: point-in-time depth-chart transport into live Props 2.1 personnel state.
- PR #449 merged: post-kickoff CI lifecycle hardening.
- PR #459 merged: a fully started target week is a governed successful no-op for the live Props refresh; it preserves the last valid capture instead of producing a false red workflow.
- The live market workflow has configured sportsbook credentials and keeps the prior publication intact on failed/partial/started-slate refreshes.

Do not rebuild these components unless repository evidence proves a regression.

## Frozen Week 2 evaluation cohort

The scientific evaluation cohort is frozen from:
- source live run: `35477049179`
- publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
- receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`
- immutable receipts: 3,439
- frozen games: 15
- players: 744

No retrospective forecast mutation is allowed. Week 2 evaluation results are evidence, not a tuning set.

## Prospective result already observed

The successful evaluation artifact from the original evaluator run graded 1,606 forecasts across 14 finalized games. There were 359 like-for-like market-matched forecasts.

On that matched cohort, the model underperformed the original sportsbook market:

- projection MAE delta (model minus market): about **+1.375 units**
- game-clustered 95% CI: **[+0.828, +2.001]**
- Brier delta (model minus market): about **+0.0243**
- 95% CI: **[+0.0066, +0.0414]**
- log-loss delta (model minus market): about **+0.1035**
- 95% CI: **[+0.0432, +0.1729]**

All preregistered probability bins showed overprediction of hit rate / overconfidence. There were zero original `MODEL EDGE` observations in the frozen cohort, so prospective ROI is not measurable from Week 2.

Interpretation: this is a one-week diagnostic cohort. It is enough to reject any current claim that Props 2.1 beats the market, but not enough to justify post-hoc parameter selection.

## Required next research sequence

1. Finish and merge the current-main evaluation harness in #458 after CI is green and the branch is rebased to current main.
2. Preserve Week 2 as locked evaluation-only evidence. Do not tune calibration, thresholds, priors, concentration, personnel weights, or efficiency coefficients against the same outcomes.
3. Open a new preregistered challenger lane for hypotheses motivated by Week 2. Highest-priority questions:
   - probability calibration / shrinkage toward 0.50;
   - decomposition of model-vs-market error by prop family and position;
   - whether opportunity means or outcome-distribution variance drive the overconfidence;
   - whether uncertainty is too narrow after injury/personnel adjustments;
   - matched-line bias by market type, player role, and book dispersion;
   - calibration conditional on distance from market and on personnel uncertainty.
4. Use a future holdout (Week 3+ prospective data) to evaluate any challenger. Do not report market superiority until multiple independent weeks/games support it with clustered uncertainty.
5. Keep collecting original market receipts even when there is no published MODEL EDGE signal. The purpose is model-vs-market validation, not just bet tracking.

## Product/UI state

The Props product QA and responsive surface are already wired and should remain research-beta labeled. Do not make UI changes that imply validated market edge. Publication should continue to expose fair lines / model information while respecting research status.

## Repository hygiene

Only active Props PR should be #458 unless a separately preregistered next-stage challenger is opened. Older duplicate/superseded Props PRs should stay closed. Prefer adding new hypotheses in a new research branch rather than modifying the frozen evaluator.

## Immediate next-chat instruction

Start by checking:
1. `main` SHA and whether #458 is rebased/green;
2. the latest `LevLine Props 2.1 post-Sunday evaluation` run and artifacts;
3. whether the Week 2 matched metrics reproduce exactly;
4. whether a new Week 3 prospective cohort has begun collecting.

Then continue from the research sequence above. Do not restart Props architecture work.
