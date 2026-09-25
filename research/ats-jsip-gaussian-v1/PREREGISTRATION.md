# ATS-JSIP-GAUSSIAN-V1 — Frozen Preregistration

**Candidate ID:** `ATS-JSIP-GAUSSIAN-V1`  
**Status:** FROZEN BEFORE IMPLEMENTATION / TARGET-SEASON SCORING  
**Program:** LevLine ATS / SpreadLine next-generation historical research  
**Production authorization:** NONE  
**Completed-2026 outcomes permitted:** 0

This document freezes the immediate successor to the structurally failed `ATS-JSIP-V1` experiment. The successor is intentionally surgical: it preserves the original joint-score, market-total, football-lattice, and qualified-moneyline mechanism while replacing only the numerically infeasible Student-t single-team kernel with an exponentially tailed Gaussian kernel and widening the fail-closed numerical ceiling prospectively.

No 2022–2025 `ATS-JSIP-V1` target performance exists. V1 failed before target probabilities or proper scores were generated. Therefore this successor is informed only by V1's pre-target numerical-support failure, not by target predictive performance.

## 1. Scientific question

Does a coherent joint distribution of home and away final scores, anchored to sportsbook spread and total, corrected for football score-lattice structure, and conservatively constrained by qualified paired-moneyline information improve exact ATS Cover/Push/Loss probability quality beyond the canonical one-dimensional `KMASS-MARKETML-IPROJ` null when the score kernel is numerically well-posed?

The hypothesis remains distributional. The candidate asks whether total-conditioned score-pair geometry contains useful information for ATS probability mass around the spread boundary that is absent from the strongest accepted one-dimensional margin null.

## 2. Exact relationship to failed ATS-JSIP-V1

`ATS-JSIP-V1` is permanently closed as `FAILED / FAIL_CLOSED_BEFORE_TARGET_SCORING`.

Its primary null reproduced successfully on 1,087 exact common 2022–2025 rows to machine precision. The failure was entirely structural: all 2,174 team-score axes failed every frozen Student-t `(df, scale)` pair at the 160-point support ceiling. Even the thinnest-tailed legal pair remained above the frozen `1e-12` omitted-tail requirement.

This successor does **not** reopen or repair V1 under the old ID.

Frozen changes versus V1 are limited to:

1. replace the discretized Student-t structural team-score kernel with a discretized Gaussian location-scale kernel;
2. remove the obsolete `df` nuisance dimension;
3. expand the numerical fail-closed ceiling from 160 to 200;
4. strengthen preflight so every legal Gaussian scale, not merely the selected scale, must satisfy the omitted-tail tolerance on every canonical target input before target scoring.

Everything else remains as close as practicable to the original mechanism so that a future result is attributable to the intended joint-score hypothesis rather than architecture sprawl.

## 3. Historical evidence boundary

Primary outer target seasons are fixed at:

`2022, 2023, 2024, 2025`.

Training/development data may use seasons `2015` through `S-1` for outer target season `S`, subject to the same chronology and eligibility rules used by the accepted ATS research program.

Any inner-model or nuisance selection for outer target season `S` must use only validation seasons strictly before `S`, and each inner validation season must itself be forecast from still-earlier training seasons.

The 2022–2025 sample is non-pristine development evidence. A favorable result may justify prospective shadow evaluation only. It can never authorize production by itself.

Completed-2026 game outcomes, 2026 ATS grades, 2026 candidate performance, or any feature derived from completed-2026 outcomes are forbidden.

## 4. Qualified inputs

### Mandatory

- sportsbook home spread `L`;
- spread-derived market home-margin center `C = -L` under the canonical sign convention;
- game identity, season, and week required for chronology and scoring.

### Optional only where historically qualified

- market total `T`;
- paired home/away moneylines converted to vig-free conditional non-tie home-win probability `u_market` using the repository's already-qualified procedure.

Historical spread-side juice is not qualified and must not be invented. Missing price is never replaced with `-110` for probability construction. The historical spread/total archive remains exact-horizon opaque and must not be relabeled as close, T-120, consensus, or constituent-book data beyond established provenance.

## 5. Market-implied team-score locations

When total `T` is available:

- `mu_H = (T + C) / 2`
- `mu_A = (T - C) / 2`

These are location anchors, not claims that market spread and total are literal mathematical expectations.

When `T` is missing, use the median historical total from the outer training fold only, `T_train_median`, and emit `total_missing = true`. The fallback may not use target-season outcomes or future totals.

## 6. Structural Gaussian team-score kernel

For team-score location `mu` and scale `sigma`, define a latent Gaussian:

`X ~ Normal(mu, sigma^2)`.

The nonnegative integer score kernel is the ordinary half-integer discretization conditional on the latent score being at least `-0.5`:

`q(s | mu, sigma) = [Phi((s+0.5-mu)/sigma) - Phi((s-0.5-mu)/sigma)] / [1 - Phi((-0.5-mu)/sigma)]`

for integer `s >= 0`.

Frozen scale grid:

`sigma in {8, 10, 12, 14}` points.

Select `sigma` only by chronology-clean prior-season inner validation observed-cell team-score log loss after applying the football score-lattice multiplier described below.

Exact nuisance ties choose the larger `sigma`.

No skew, mixture component, Student-t degree of freedom, team-specific scale, spread bucket, total bucket, or target-dependent scale is permitted in this candidate.

## 7. Adaptive numerical support

The Gaussian kernel is mathematically unbounded, so finite score support is a numerical approximation only and must remain non-folded.

For each team marginal:

1. begin with score support `0..80`;
2. compute conditional omitted upper-tail mass
   `P(X >= B+0.5 | X >= -0.5)` at current bound `B`;
3. if the omitted mass exceeds `1e-12`, expand both team-score axes by 20 points;
4. repeat until every relevant team marginal is below `1e-12`;
5. never fold omitted mass into the endpoint;
6. fail closed if any row requires support above `200`.

### Strong pre-target feasibility gate

Before any target-season candidate probability is generated, the implementation must evaluate **every canonical target input row under every legal `sigma in {8,10,12,14}`** and prove that the omitted upper-tail tolerance is achievable at or below 200 for both team axes.

This feasibility sweep may use spread, total, game identity, season, week, and chronology-safe total fallback inputs. It may not read or condition on target final scores, target margin, ATS grade, or any completed-2026 outcome.

If even one canonical target input / legal-scale combination fails this gate, the candidate is `FAILED` before target scoring. The scale grid, tolerance, or support ceiling may not then be altered under this ID.

## 8. Football score-lattice multiplier

Preserve the V1 score-lattice mechanism.

For outer season `S`, estimate a league-wide single-team integer-score multiplier using only the outer training fold. For each score cell `s`, compare empirical training-fold frequency with aggregate probability under the candidate Gaussian kernel at each row's market-implied team-score location. Apply symmetric Dirichlet shrinkage before forming the empirical/model ratio.

Frozen total pseudocount grid:

`alpha in {25, 100, 400}`.

Select `alpha` using pooled chronology-clean prior-season inner validation observed-cell team-score log loss only. Exact ties choose the larger pseudocount.

No manually selected score bonuses are allowed. Cells absent from a training fold remain finite and positive through shrinkage.

After multiplying by the lattice weights, each home and away marginal is renormalized on the adaptive support. The unprojected joint prior is their product.

No separately fitted score-correlation parameter is allowed in this candidate.

## 9. Qualified moneyline information projection

When qualified paired-moneyline probability `u_market` exists, apply the same minimum-KL sign-mass projection semantic class as the accepted canonical null and V1:

`P(H>A | H!=A) = u_market`.

The projection must preserve the pre-projection tie mass `P(H=A)`. Positive-margin and negative-margin score-pair cells are rescaled only enough to satisfy the qualified conditional non-tie home-win probability, preserving relative probabilities within each sign region.

When paired moneyline is unavailable, no synthetic probability is created. The unprojected joint prior is retained and `ml_missing = true` is reported.

## 10. Margin and ATS probabilities

After optional moneyline projection, marginalize exactly:

`P(M=m) = sum_{H-A=m} P(H,A)`.

For home spread `L`:

- Cover if `M + L > 0`;
- Push if `M + L = 0`;
- Loss if `M + L < 0`.

Half-point spreads therefore have zero push probability. Whole-number spreads retain the exact matching margin-cell push probability.

No direct CPL classifier, ATS-side threshold, or ROI-optimized decision rule is part of this candidate.

## 11. Chronological nuisance selection

For outer target season `S`, select `(sigma, alpha)` using expanding rolling-origin validation seasons strictly before `S`.

Each inner validation season must be forecast only from still-earlier training seasons. Pool observed-cell team-score log loss across eligible inner validation rows.

Frozen minimum eligible inner-training rows: `100`.

If an outer season lacks at least 100 eligible chronology-safe inner-training rows for the frozen selection protocol, fail closed rather than invent a fallback.

No target-season candidate result, ATS grade, CPL score, hit rate, or ROI may influence nuisance selection.

## 12. Required nulls

Primary null:

`KMASS-MARKETML-IPROJ`

It must reproduce on the exact accepted canonical common rows and accepted nuisance freeze before candidate target scoring.

Also report the existing market-only `M0/M1/M2` hierarchy where mechanically available for continuity. These remain diagnostics and cannot replace the stronger primary null.

## 13. Primary and secondary metrics

### Primary selector

Multinomial Cover/Push/Loss log loss on exact common eligible rows, reported as:

`candidate CPL log loss - KMASS-MARKETML-IPROJ CPL log loss`.

Lower is better; negative delta favors the candidate.

### Secondary non-selective diagnostics

- CPL multiclass Brier;
- conditional non-push cover Brier and log loss;
- integer-margin observed-cell log score;
- discrete ranked probability / CRPS-style score;
- calibration intercept/slope where estimable;
- reliability, resolution, and sharpness;
- expected/median margin error;
- push calibration overall and in already-frozen key-number buckets;
- ATS W-L-P and non-push hit rate;
- per-season paired CPL deltas;
- leave-one-season-out and leave-one-week robustness;
- frozen favorite-size and market-total diagnostic buckets from the existing ATS evaluation protocol.

Historical ROI under assumed `-110` may appear only as the repository's explicitly labeled `REFERENCE_MINUS110` sensitivity. It is not an actual quoted-price result and is not a selector.

## 14. Uncertainty

Use exact common rows and paired losses.

Final evidence uses `10,000` season-stratified NFL-week block bootstrap resamples with fixed seed `20260924`.

Report the paired 95% percentile interval and bootstrap probability that candidate CPL log loss is lower than the primary null.

No alternative resampling scheme may be substituted after target results are visible.

## 15. Advancement gate

Label `HISTORICALLY_PROMISING` only if all conditions hold:

1. aggregate primary CPL delta versus `KMASS-MARKETML-IPROJ` is strictly favorable;
2. paired 95% bootstrap interval has no material adverse tail and bootstrap probability candidate-better is at least `0.80`;
3. at least 3 of 4 outer seasons have non-adverse CPL point deltas;
4. every normalization, support, chronology, identity, mutation-invariance, and leakage test passes;
5. calibration shows no material systematic failure;
6. aggregate improvement is not solely explained by one season, week, or preregistered diagnostic bucket.

`ELIGIBLE_FOR_PROSPECTIVE_SHADOW` additionally requires repository validation and production-firewall checks to pass on the exact accepted head.

If aggregate primary CPL delta is non-favorable, classification is `NO_MATERIAL_IMPROVEMENT` regardless of hit rate or ROI.

Structural/numerical invalidity is `FAILED` and remains failed; there is no post-result rescue under this ID.

## 16. Mandatory preflight invariants before target scoring

The implementation phase must prove before generating any target-season candidate score:

1. completed-2026 outcomes enter no frame;
2. all nuisance fits for outer target season `S` use seasons `<S` only;
3. mutating target final home score, final away score, actual margin, or ATS grade cannot change forecast probabilities;
4. every canonical target input under every legal `sigma` satisfies omitted upper-tail mass `<1e-12` at support `<=200` for both team axes;
5. all constructed marginals and joint PMFs are finite, nonnegative, and normalized within `5e-11`;
6. moneyline projection preserves tie mass within `1e-12` and matches qualified conditional non-tie `u_market` within `2e-11`;
7. half-point spread push probability is zero within numerical tolerance;
8. whole-number spread push probability equals the exact matching marginalized margin cell;
9. canonical primary-null row identities and accepted hashes reproduce before candidate scoring;
10. no production/protected forecasting surface changes.

Any failure stops target scoring immediately.

## 17. Explicitly forbidden mutations

After this freeze, do not:

- reintroduce Student-t under this candidate ID;
- change the scale grid `{8,10,12,14}`;
- change the pseudocount grid `{25,100,400}`;
- relax the `1e-12` tail tolerance;
- increase the 200-point support ceiling;
- fold omitted tail mass into the endpoint;
- add skewness, Gaussian mixtures, score correlation, team-specific scales, or score-pair interactions;
- add EPA, Elo, QB, injury, personnel, weather, or other football-feature residual learning;
- add spread-bucket or total-bucket gating;
- add smooth moneyline-residual shape tilts already rejected by ATS Market Manifold V2;
- optimize on ATS hit rate or ROI;
- inspect completed-2026 outcomes;
- modify production F-ST, LevLine, Sunday Signal, fair-line, signal, or publication behavior.

Any scientifically justified extension requires another candidate ID and another preregistration.

## 18. Next phase boundary

Once this preregistration is canonical, the next phase may implement the frozen Gaussian joint-score machinery, invariance/unit tests, research-only workflow, primary-null reproduction, and chronology-correct 2022–2025 historical evaluation.

The preregistration commit must remain identifiable as the controlling pre-result commit. No target-season candidate probability or proper score may be generated on a commit earlier than, or inconsistent with, this frozen contract.
