# ATS Market Manifold V2 — Frozen Experiment Contract

This contract is frozen before any V2 target-season candidate score is generated.

## 1. Historical sample

Primary outer seasons: `2022, 2023, 2024, 2025`.

Use the canonical schedule/game identities and the immutable archived historical `market_prob` surface already accepted by ATS Cross-Market Transfer V1. Primary comparisons use exact common paired rows. Completed-2026 outcomes must equal zero in every execution receipt.

The 2022–2025 sample is development/non-pristine. It is suitable for falsification and architecture comparison but not an independent prospective confirmation set.

## 2. Baseline PMF

For each target season, reuse the accepted prior-only `CONSTANT_SCALE_KEY` nuisance fit from `research/ats-historical-challenger/v2_nuisance_freeze.json`.

The baseline discrete margin PMF is the accepted Student-t integer-cell distribution with finite log-mass adjustments only at `0`, `±3`, and `±7`.

Frozen restrictions:

- spread-derived `spread_line` remains the location parameter;
- constant scale only;
- no conditional scale;
- no new key numbers;
- no center correction;
- no football features;
- no F-ST/LevLine probability in the primary candidate;
- no hard finite support;
- no endpoint folding;
- no modeling-time probability clipping.

Numerical support expands symmetrically until omitted baseline tail mass is `< 1e-12`.

## 3. Strong null N1

`KMASS-MARKETML-IPROJ` is the required primary null.

For baseline q, preserve q(0). Let q+ and q- be baseline positive and negative mass. Let u be the immutable archived market conditional non-tie home-win probability. Multiply positive cells by `((1-q0)u/q+)`, negative cells by `((1-q0)(1-u)/q-)`, and leave zero unchanged.

This must exactly reproduce the accepted V1 market-moneyline null on the 1,087 canonical V1 rows to numerical tolerance before V2 target scoring is accepted.

## 4. Market residual

Define baseline conditional non-tie win probability

`u_q = q+ / (q+ + q-)`.

Define

`r_ml = logit(p_market) - logit(u_q)`.

The archived `market_prob` semantic class is inherited exactly from V1. It must not be relabeled as closing, T-120, consensus, or de-vigged paired-book probability when those semantics are not established by the archive.

## 5. Candidate A — ATS-MM-SHAPETILT-V1

Start from N1 probabilities `p0(m)` on adaptive integer support.

Frozen shape basis:

`h(m,L) = tanh((m-L)/3)`.

For `gamma = theta * r_ml`, define raw nonzero weights

`w(m) = p0(m) * exp(gamma*h(m,L))`.

Then renormalize positive and negative cells separately back to N1's exact positive and negative total masses. Keep the zero cell exactly fixed. This guarantees:

- total probability one;
- N1 market-moneyline sign totals unchanged;
- tie mass unchanged;
- only within-sign relative mass changes.

Use stable log-sum-exp arithmetic. Any nonfinite value or normalization violation fails closed.

## 6. Candidate B — ATS-MM-SHAPETILT-MEANFIX-V1

Use the same N1 base, `h`, `r_ml`, and selected theta as Candidate A.

Define

`w_lambda(m) = p0(m) * exp(gamma*h(m,L) + lambda*m)`

for nonzero cells, with separate positive/negative normalizers enforcing N1 sign totals exactly. Zero remains fixed.

Solve scalar `lambda` so the adaptive-support expected margin equals **N1's adaptive-support expected margin before the shape tilt**. This prohibits any additional mean drift beyond the strong market-moneyline null while leaving higher-order within-sign shape free to change. Use a deterministic bracket expansion plus Brent root solve. At `theta=0`, lambda must resolve to zero within tolerance and Candidate B must reproduce N1. If the constraint is infeasible or numerical tolerance fails, fail the row closed.

Required tolerances:

- normalization error `<= 5e-11`;
- sign-mass error `<= 2e-11`;
- zero-mass error `<= 1e-12`;
- N1 expected-margin error `<= 2e-9`;
- omitted baseline tail `< 1e-12`.

## 7. Frozen theta selection

Grid:

`{0, .25, .50, .75, 1.00, 1.50, 2.00}`.

For outer season S, select theta for Candidate A using only rows with season `< S`, scored with nuisance fits trained strictly before each inner validation season. Selection metric is pooled mean multinomial CPL log loss. Exact ties choose smaller theta.

Candidate B inherits Candidate A's theta. It receives no separate tuning grid.

No target-season result may influence theta selection.

## 8. Mandatory invariance tests before target scoring

Preflight must prove:

1. theta=0 reproduces N1 CPL probabilities within `1e-12` for both Candidate A and Candidate B;
2. Candidate A and B preserve N1 positive, negative, and zero masses;
3. Candidate B preserves N1 expected margin;
4. half-point spreads have zero push mass;
5. whole-number spreads retain positive push mass when the corresponding cell has positive PMF mass;
6. mutating `actual_margin` before scoring does not change any forecast probability;
7. no row from 2026 enters the archive;
8. every historical F-ST field, if present for provenance diagnostics, is ignored by the V2 primary scoring functions;
9. canonical V1 game-identity hash/common-row counts match before scoring.

## 9. Evaluation

Primary: multinomial Cover/Push/Loss log loss.

Secondary, non-selective:

- CPL multiclass Brier;
- conditional non-push cover Brier/log loss;
- calibration intercept/slope;
- reliability/resolution/sharpness;
- integer-margin observed-cell log score;
- discrete RPS/CRPS-style score;
- expected-margin MAE;
- ATS W-L-P and exact Clopper-Pearson interval;
- candidate-vs-N1 side-switch record;
- per-season deltas;
- leave-one-season-out and leave-one-week robustness;
- fixed descriptive spread/key-number/`|r_ml|` diagnostics.

The bootstrap is deterministic: 10,000 paired season-stratified NFL-week block resamples, seed `20260924`. Candidate A and B form one multiplicity family with Holm adjustment for the two primary candidate-vs-N1 comparisons.

## 10. Classification

`IMPLEMENTATION_CANDIDATE` requires every gate in `PROGRAM.md`.

`HISTORICALLY_PROMISING` may be used only for an aggregate favorable point estimate that fails one or more uncertainty/stability gates without leakage/numerical invalidity.

`NO_MATERIAL_IMPROVEMENT` applies when there is no qualifying aggregate gain.

`FAILED` applies to leakage, chronology, identity, or numerical invalidity.

No post-result calibration, basis replacement, theta-grid expansion, total-line interaction, spread-bucket gating, or selective subset can promote a candidate.