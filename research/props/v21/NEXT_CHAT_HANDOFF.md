# LevLine Props 2.1 — Next Chat Handoff

**Updated:** 2026-09-21 PT / 2026-09-22 UTC  
**Repository:** `levine26/nfl-forecast-model`  
**Purpose:** authoritative continuation point for autonomous Props work. Do not restart the project or re-audit completed lanes unless current repository evidence shows a regression.

## 1. Current production/research state

The current Props path is **Props 2.1**, not the older Props 2.0 experimental PR stack.

Already merged into `main`:
- PR #445 — structured official availability transport/QA.
- PR #446 — point-in-time depth-chart personnel transport into live Props 2.1.
- PR #434 — full eligible-roster concentration regression lock.
- PR #449 — post-kickoff CI lifecycle hardening.

Active canonical PRs:
- **#466** — canonical current-main frozen Props 2.1 prospective evaluation. It replaces #447/#448/#457/#458.
- **#459** — MERGED. Post-kickoff live refresh is now an audited successful no-op that preserves the last valid pregame publication; missing state for any upcoming game still fails closed.

Do not recreate or compete with these PRs. Inspect their latest head/checks and continue them.

## 2. Frozen Week 2 evidence boundary

The primary prospective cohort is immutable and must remain unchanged:

- source live workflow run: `35477049179`
- frozen publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
- frozen receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`
- total frozen receipts: **3,439**
- frozen games: **15**
- frozen players: **744**
- model: `levline-props-2.1-sunday-v0.1`

No completed-game outcome may be used to rewrite those forecasts, thresholds, priors, probabilities, or signal labels.

## 3. First prospective evaluation result

The successful post-Sunday evaluation artifact from workflow run `35662662103` graded:

- **1,606** forecasts across **14** finalized games.
- **359** like-for-like market-matched forecasts across **14** games and **193** players.
- **223** receipts remained ungraded because their game was not final at the evaluation cutoff.
- **1,506** receipts lacked a matched positive/zero snap participation record and require a data-quality/eligibility audit.
- **104** were voided for zero offensive snaps.
- There were **0 original MODEL EDGE observations**, so ROI is **not measurable**.
- There were **0 matched closing-market observations**, so CLV/closing-line comparison is **not measurable**.
- Exact CRPS/PIT/interval coverage is unavailable because the frozen receipt did not preserve a lossless distribution/interval representation.

### Matched market comparison

On the 359 matched observations:

- Props 2.1 Fair Line MAE: **11.9833**
- original sportsbook line MAE: **10.6086**
- paired Fair-Line-minus-market absolute-error difference: **+1.3747**
- game-clustered 95% CI: **[+0.8275, +2.0014]**

Probability scoring:

- model Brier: **0.27072**
- market no-vig Brier: **0.24645**
- model-minus-market Brier difference: **+0.02426**
- 95% game-clustered CI: **[+0.00664, +0.04139]**

- model log loss: **0.78946**
- market no-vig log loss: **0.68596**
- model-minus-market log-loss difference: **+0.10350**
- 95% game-clustered CI: **[+0.04323, +0.17289]**

Positive differences above mean the model was worse than the market on this cohort.

### Calibration diagnostic

All five preregistered probability bins overpredicted realized hit rate. Representative gaps:

- 50–55% bin: **-8.75 pp**
- 55–60% bin: **-24.93 pp**
- 60–65% bin: **-14.82 pp**
- 65–70% bin: **-13.62 pp**
- 70%+ bin: **-21.23 pp**

Expected calibration error: **0.1691**.

This is a strong **hypothesis-generation signal for overconfidence**, but it is still only one week / 14 finalized games and may not be used for retrospective tuning.

## 4. Scientific interpretation

The correct current conclusion is:

1. Props 2.1 has **not demonstrated market superiority**.
2. On the first frozen prospective cohort, the market outperformed Props 2.1 on matched line MAE, Brier, and log loss.
3. The model appears materially overconfident on this cohort.
4. The sample is not sufficient for a stable multi-week conclusion.
5. The system correctly emitted no MODEL EDGE bets, so there is no legitimate ROI claim.
6. The value of Props 2.1 on this cohort is currently more evident in **QA/intelligence/failure prevention** than in incremental predictive accuracy.

Do not soften, hide, or reverse these findings. Scientific validity is more important than an impressive result.

## 5. Immediate priority order

### P0 — finish lifecycle/reproducibility cleanup

1. #459 is merged; verify future post-kickoff live refreshes continue to no-op cleanly.
2. Get #466 green and merge it so the prospective evaluator and evidence contract live on current main.
3. Re-run/verify the post-Sunday evaluation from current main and compare its summary fingerprint/metrics to run `35662662103`. Any material delta requires investigation before further model work.

### P1 — strengthen future evidence collection before changing the model

4. **Capture closing market observations** before kickoff so CLV and closing-line/no-vig comparison become measurable.
5. **Preserve lossless forecast distributions or reproducible distribution parameters/seeds** in immutable receipts so CRPS, PIT, and interval coverage can be calculated prospectively.
6. Audit the **1,506 missing participation** exclusions. Determine how much is legitimate inactive/bench absence versus player-ID/snap-source coverage. Fix only source/identity mechanics; do not infer participation from final outcomes.
7. Continue collecting immutable weekly cohorts. Keep Week 2 frozen as evaluation-only evidence.

### P2 — preregister successor challengers; do not tune against Week 2

Week 2 can motivate hypotheses, but parameter choices must come from leakage-free prior-only research or future holdout evaluation.

Priority challenger hypotheses:

- **Probability calibration / shrinkage:** test fixed, preregistered calibration families (for example logit-temperature shrinkage or beta calibration) using only leakage-free training data. Do not fit parameters to Week 2.
- **Market-assisted challenger:** separately test a market-prior/blended probability challenger by prop family. Keep it distinct from the pure model so incremental information beyond market remains measurable.
- **Availability/workload mixtures:** exploit the newly merged structured official availability + point-in-time depth-chart evidence, while preserving fail-closed workload uncertainty.
- **Route/target opportunity quality:** revisit route participation and target-share evidence only with point-in-time reproducible sources.
- **Support-correct distributions:** revisit count/yardage distribution families so support, tails, and variance are empirically defensible.
- **Matchup residual signal:** only promote defensive/efficiency adjustments that pass true pregame rolling-origin tests after controlling for market and player opportunity state.

Every challenger needs an explicit pre-outcome contract, frozen feature set, frozen parameters, and a future holdout or leakage-free rolling-origin evaluation.

## 6. What not to do

Do **not**:
- tune calibration, thresholds, distributions, or coefficients to make Week 2 look better;
- create retrospective MODEL EDGE bets;
- reconstruct fake pregame sportsbook quotes from postgame data;
- infer injury/availability/participation from whether the player ultimately played;
- merge old Props 2.0 experiment branches wholesale into current production;
- claim that test-suite success is predictive accuracy;
- claim market superiority from this one-week result;
- alter F-ST / the official LevLine winner model as part of Props work.

## 7. Older Props PR cleanup policy

The large Props 2.0 research stack (#360, #366, #372, #373, #375, #376, #380, #383, #384, #385, #386, #394, #408 and related branches) is historical research evidence, not the current integration path.

Close/archive stale PRs once their unique finding is either:
- represented in this handoff / the current research registry, or
- explicitly retained by branch/PR history for future hypothesis work.

Closing a research PR does not delete its commits. Re-open or port a specific finding only when it maps to a preregistered Props 2.1 successor experiment.

PR #414 (DraftKings tertiary fallback) is also not a current blocker because current main has configured PropLine support plus a credential-free PropLine public-demo fallback. Keep/revive DraftKings only if live market coverage evidence shows the present provider chain is inadequate.

## 8. Sunday Signal interaction

Props work must not modify the official LevLine/F-ST winner probabilities.

The separate Sunday Signal editorial repair is addressing post-kickoff contraction of `this_week.csv` / Reads. Props should consume governed stable inputs, but should not wait for editorial prose work when the frozen Props cohort and research evidence are already available.

## 9. Definition of meaningful next progress

A next chat should prefer completing one of these concrete outcomes over producing another roadmap:

- keep #459 lifecycle behavior green on future post-kickoff runs;
- merge #466 after reproducible evaluation succeeds;
- produce and freeze a closing-market capture contract;
- resolve the missing-participation audit with quantified causes;
- preregister one successor calibration/market-assist challenger without using Week 2 outcomes for parameter selection;
- collect the next immutable prospective cohort.

If none of those are being advanced, the Props program is probably being delayed by process rather than science.
