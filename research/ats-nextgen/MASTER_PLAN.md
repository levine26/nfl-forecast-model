# LevLine ATS Next-Generation Research Program — Master Plan

Status date: 2026-09-23
Program owner: research only
Production authority: none

## Purpose

This program tests whether LevLine can improve ATS probability estimation by reformulating NFL spread betting as conditional margin-distribution and cover-probability estimation around the exact quoted market proposition rather than as unconditional mean-margin prediction.

The program does **not** reopen the completed Spread & Points Next-Generation hypotheses. Prior negative evidence is accepted as fixed. In particular, the historical market beat the independent LevLine margin model in MAE, large model/market disagreement was not a validated edge, A0/B0/C0 failed their incremental tests, Candidate 5 did not improve F-ST, and generic historical residual stacking is closed.

The sole scientific novelty admitted here is the ATS-specific target: conditional quantiles, a discrete NFL margin distribution with push/key-number mass, and direct cover/push/loss probability estimation under chronology-clean market baselines.

## Fixed sign convention

For every experiment:

- `M = home_score - away_score`.
- `L = sportsbook home spread`, conventional sportsbook sign (home favorite is negative; e.g. home -3 means `L=-3`).
- `S = -L` is the market-implied home winning margin.
- `R = M + L = M - S` is the canonical market-relative residual.
- home cover iff `R > 0`;
- push iff `R = 0`;
- home ATS loss iff `R < 0`.

This convention is immutable for Phase 2. Synthetic grading tests are mandatory before any historical experiment can run.

## Fixed prior evidence

The following are development facts, not hypotheses to rescue:

- 2022–2025 baseline reproduction: independent margin MAE approximately 9.962; historical market spread MAE approximately 9.494; raw model-side ATS hit rate approximately 48.77% excluding pushes.
- Large disagreement did not validate an edge; >=6-point model/market disagreements were materially worse in continuous error.
- A0 did not beat the market as a standalone margin model.
- B0 did not beat the market.
- C0 did not establish incremental football information around a late/closing market benchmark.
- Candidate 5 did not improve F-ST.
- Generic historical mean-residual stacking is closed.

Therefore Q1 is not a renamed C0. Q1 differs only by its preregistered conditional-quantile objective and ATS-relevant targets.

## Core scientific hypothesis

Let `M` denote final home margin and `X` the point-in-time-safe game/market state. The useful estimands for spread wagering are not limited to `E[M|X]`. They include conditional quantiles and discrete wager-outcome probabilities:

- `Q_0.476190...(M|X)`;
- `Q_0.500000...(M|X)`;
- `Q_0.523809...(M|X)`;
- `P(cover | L, price, X)`;
- `P(push | L, X)`;
- `P(loss | L, price, X)`.

The 0.476190/0.523810 quantiles are the equal-juice, continuous/no-push reference implied by standard -110 economics. They are **not** a universal betting threshold. Exact side price and non-zero push mass govern wager EV when available.

## Primary market nulls

The sportsbook market is the primary null, not merely a feature.

### M0 — quoted spread

The quoted market home spread with no LevLine adjustment. This is the primary median/fair-line benchmark.

### M1 — market-derived probability distribution

A chronology-clean discrete PMF centered directly at `S=-L`, with conditional scale driven only by `abs(S)`, market total, and the frozen `abs(S) x (total-45)` interaction, plus prior-history key-number mass. M1 uses no football state and no Q1 residual correction. Paired moneyline is diagnostic only for M1.

### M2 — market plus simple line-level calibration

The same market-only discrete PMF, but centered at `S + q1_m2_median_residual`, where `q1_m2` is the chronology-clean market-only Q1 quantile calibration using spread, total and paired-moneyline no-vig probability when available. No football information. M2 isolates whether any improvement is merely market-shape calibration rather than incremental football information.

Q1/Q2/Q3 earn an incremental claim only against the relevant market null. Calibration usefulness and incremental football information are separate claims.

## Exactly three Phase-2 primary experiments

### Q1 — `Q1-QR-MARKET-RESIDUAL-V1`

Question: can compact PIT-safe football/market state improve the conditional quantiles of `R=M+L` around the sportsbook line?

Frozen targets: tau in `{10/21, 1/2, 11/21}` = `{0.4761904762, 0.5, 0.5238095238}`.

Frozen learner family: regularized linear quantile regression only. No nonlinear tournament. Hyperparameter grid and features are specified in `Q1_QUANTILE_PREREGISTRATION.md`.

### Q2 — `Q2-DISCRETE-KEY-PMF-V1`

Question: does a discrete, heavy-tail-capable, key-number-aware NFL margin PMF improve cover/push/loss probabilities relative to the existing fixed Normal bridge and market-only nulls?

Frozen support: integer home margins `k=-75,...,+75`, with probability outside the bounds folded into endpoint tail bins.

Frozen base-family comparison: Gaussian, Student-t, generalized normal. The selection rule is inner chronology-clean proper score only; no outer ATS selection. An empirical residual PMF is a benchmark, not an unrestricted candidate family. Finite-mixture models are excluded from V1.

Frozen explicit excess-mass set: `K={0, ±3, ±6, ±7, ±10, ±14}`. Parameters are learned from prior history only.

### Q3 — `Q3-DIRECT-CPL-V1`

Question: does direct cover/push/loss modeling add incremental probability information beyond Q1/Q2?

Frozen learner comparison: regularized multinomial logistic reference plus one deliberately shallow XGBoost challenger. Hyperparameters are bounded in advance. Probability calibration is one-scalar temperature scaling fitted only on prior inner OOF predictions.

## Q2/Q3 blend authorization

A probability blend is authorized **only** as a preregistered inner-validation operation:

`P_blend = w * P_Q2 + (1-w) * P_Q3`

with `w in {0, .25, .50, .75, 1}`.

The weight is selected on prior-time inner OOF rows using multinomial log loss. It is never chosen from ATS hit rate, realized ROI, or the outer evaluated season. Endpoints are allowed, so blending is not forced.

## Historical evidence boundary

The modern scoring-regime V1 floor is the 2015 regular season. The 2015 extra-point rule change is the regime boundary; pre-2015 key-number frequencies are not assumed exchangeable with V1.

Outer development seasons are exactly `2022, 2023, 2024, 2025`.

These seasons have already been heavily inspected in LevLine research and are explicitly **non-pristine development evidence**. They may support mechanism testing, OOF comparison, calibration and rejection, but positive historical results alone cannot authorize production.

Any candidate surviving Phase 3 requires a future prospective shadow phase.

## Completed-2026 firewall

Completed 2026 outcomes are prohibited from architecture, feature, family, quantile, distribution, key-mass, threshold, hyperparameter, calibration, blend or rescue decisions.

Outcome-blind 2026 market/input observations may be inspected only for source qualification and pipeline feasibility. They are not candidate evaluation evidence.

## Frozen chronology

Random K-fold is prohibited.

For outer season `Y in {2022,2023,2024,2025}`:

1. Eligible model history begins in 2015.
2. Inner validation seasons are `t in {2019,...,Y-1}`.
3. Each inner fold `t` trains on seasons `2015,...,t-1` and validates on season `t`.
4. Hyperparameters/model family/calibration/blend weights are chosen using pooled inner OOF predictions, with each validation season weighted equally, and only the preregistered proper score for that decision.
5. The chosen specification is refit using all eligible data `2015,...,Y-1`.
6. Outer season `Y` is predicted once with no same-season outcome updating.
7. Q1 predictions consumed by Q2/Q3 must themselves be chronology-clean OOF predictions at the relevant row.
8. Q2 probabilities consumed by Q3 must themselves be chronology-clean at the relevant row.
9. Probability calibration is learned only from prior inner OOF rows.

## Market snapshot estimand

Historical 2022–2025 schedule market fields do not establish an exact book or capture timestamp. They are treated as a generic late/closing development benchmark and labeled as such.

The existing T-120 selector is a prospective PIT-safe horizon mechanism, but it does not reconstruct historical spread-side juice/book identity. Phase 2 must not silently equate these two market objects.

Where exact contemporaneous spread price is absent, actual-price EV/ROI is unavailable. A standard -110 sensitivity analysis may be reported only as a sensitivity, never as observed market economics.

## Compact V1 feature principle

No kitchen sink. V1 is viable without a new personnel reconstruction.

Historical football state is limited to existing pregame, one-game-shifted team-strength features derived from the current feature pipeline: Elo context, rest difference, and compact EWMA differentials for offensive EPA, passing EPA, rushing EPA, success rate, defensive EPA allowed, defensive passing/rushing EPA allowed, defensive success allowed, and recent win rate. Lag-window variants are excluded from V1 unless a specific preregistration names them.

Market features are limited to quoted spread, absolute spread, total, both-moneyline no-vig home probability when available, and the explicitly frozen spread x total interaction. Historical line movement, book dispersion and spread-side price are not fabricated.

Large player-state/injury/QB reconstruction is reserved for a separate later program. Existing market variables are expected to aggregate much of that information; the ATS formulation is tested first.

## Program phases

### Phase 1 — Deep ATS Research, Problem Reformulation & Preregistration

Research, evidence boundary and immutable experiment contracts. No Q1/Q2/Q3 training or performance generation. This phase.

### Phase 2 — Controlled Implementation & Historical Development

Implement exactly the frozen Q1/Q2/Q3 contracts, synthetic grading tests, market nulls and chronology-clean 2022–2025 development evaluation. No production changes.

### Phase 3 — Scientific Synthesis, Candidate Selection & Freeze

Using the preregistered evidence, classify each architecture as `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`. No production promotion.

### Phase 4 — Conditional future prospective shadow

May start only if Phase 3 earns eligibility and a new explicit authorization starts the phase. No automatic start.

## Governance

- Scientific validity dominates favorable results.
- Null/negative results are first-class outcomes.
- No model-family rescue after outer results.
- No threshold fishing.
- No historical ROI optimization.
- No selective-subset mining beyond frozen subsets.
- No completed-2026 outcomes.
- No production F-ST or Sunday Signal modification.
- Phase 2 starts only from the merged Phase-1 contract.

## Canonical supporting documents

See all files in `research/ats-nextgen/`, especially the three experiment preregistrations, `EVALUATION_PROTOCOL.md`, `CHRONOLOGY_AND_EVIDENCE_BOUNDARY.md`, `ATS_ECONOMICS_AND_EV_CONTRACT.md`, and `RED_TEAM_AND_LEAKAGE_CHECKLIST.md`.