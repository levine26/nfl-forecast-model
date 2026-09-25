# ATS-JSIP-GAUSSIAN-V1 — Implementation Specification

**Status:** FROZEN BEFORE TARGET-SEASON CANDIDATE SCORING  
**Controlling preregistration merge:** `77e7b14a93584f97e2fb677af6eaf4c3e08cd9b3`  
**Candidate:** `ATS-JSIP-GAUSSIAN-V1`  
**Completed-2026 outcomes used:** 0  
**Target candidate results inspected before this specification:** 0

This file resolves implementation details that were intentionally left at mathematical-description level in the preregistration. It does not change the frozen model family, nuisance grids, data boundary, support tolerance, support ceiling, primary null, primary metric, bootstrap, or advancement gate.

## 1. Historical row construction

Use the accepted probability-only historical scaffold from `research/ats-crossmarket-transfer/probability_only_entrypoint.py`.

The canonical primary target universe is the exact 1,087 accepted common rows across 2022–2025. Canonical row identity and the accepted `KMASS-MARKETML-IPROJ` OOF artifact hash must reproduce before candidate target scoring.

For score-kernel nuisance fitting, use regular-season historical games from 2015 through the season immediately preceding the relevant forecast season, with finite spread, total, home score, and away score. Each game contributes two observed team-score cells.

## 2. Gaussian score cells

For integer score `s >= 0`, location `mu`, and legal `sigma`, use the preregistered conditional half-integer Gaussian cell probability exactly.

Numerically evaluate omitted upper tails with `scipy.stats.norm.sf`, not `1-cdf`, to avoid cancellation in extreme tails.

## 3. Lattice multiplier domain and shrinkage

The league-wide score-lattice multiplier is estimated on the fixed calibration cells `s = 0..80`. This domain is frozen before target scoring because it covers the initial numerical support and the empirically relevant NFL score range while preventing unobserved extreme-tail cells from receiving artificial pseudocount leverage.

For a training fold with `N` eligible games there are `2N` team-score observations. Let:

- `n_s` = number of observed home/away final scores equal to `s`;
- `g_s` = average structural Gaussian probability of score cell `s` across the corresponding `2N` market-implied team-score locations under candidate `sigma`;
- `K = 81` cells.

For frozen total pseudocount `alpha`, define the symmetric-Dirichlet shrunken empirical frequency:

`f_s = (n_s + alpha/K) / (2N + alpha)`.

The multiplier is:

`w_s = f_s / max(g_s, 1e-15)` for `s in 0..80`.

For represented score cells above 80, set `w_s = 1.0`.

No clipping, smoothing, manually selected key scores, or target-dependent adjustment is applied to `w_s` beyond the frozen Dirichlet shrinkage.

For a forecast row, multiply each represented structural Gaussian score-cell probability by `w_s` and renormalize the represented marginal. Structural omitted-tail feasibility is assessed before this renormalization, exactly as preregistered.

## 4. Chronological nuisance selection

For outer target season `S`, legal candidates are the Cartesian product:

- `sigma in {8,10,12,14}`;
- `alpha in {25,100,400}`.

Use expanding rolling-origin inner validation seasons from 2016 through `S-1` when eligible. For each validation season `V`:

1. fit the lattice multiplier on seasons `2015..V-1` only;
2. require at least 100 eligible training games before fitting;
3. use the training-fold median total only for missing-total fallback;
4. score both observed home and away final-score cells in season `V` using the fitted lattice-adjusted marginal;
5. pool negative log probability across all eligible team-score observations and all eligible validation seasons.

Choose the pair with minimum pooled observed-cell team-score log loss. Exact ties choose larger `sigma`, then larger `alpha`, matching the preregistered regularization preference.

After selection, refit the lattice multiplier for outer season `S` on all eligible seasons `2015..S-1` using the selected pair.

## 5. Joint prior and moneyline projection

The unprojected joint prior is the outer product of the normalized home and away score marginals on the common adaptive support.

If qualified `u_market` exists:

- preserve diagonal tie mass exactly;
- rescale `H>A` cells uniformly within that region so their total mass becomes `(1-tie_mass) * u_market`;
- rescale `H<A` cells uniformly within that region so their total mass becomes `(1-tie_mass) * (1-u_market)`.

This is the closed-form minimum-KL projection for the frozen sign-mass constraint and preserves relative score-pair probabilities within each sign region.

If moneyline is unavailable, retain the unprojected joint prior.

## 6. Preflight ordering

No target candidate proper score or ATS result may be computed until all of the following pass on the frozen implementation commit:

1. completed-2026 firewall;
2. canonical target-row identity and primary-null reproduction;
3. all-row/all-legal-scale Gaussian support-feasibility sweep;
4. nuisance chronology audit;
5. finite/nonnegative/normalization invariants;
6. moneyline tie-preservation and conditional-win constraint tests;
7. half-point and whole-number push identities;
8. target-outcome mutation invariance;
9. production/research path firewall.

The support-feasibility sweep is allowed to inspect only pre-outcome inputs and chronology-safe total fallback values.

## 7. Calibration diagnostic operationalization

For the frozen advancement gate's phrase `no material systematic calibration failure`, use conditional non-push cover probability on all exact common rows. Fit a logistic calibration regression of observed non-push cover outcome on the candidate logit probability.

Flag a material systematic calibration failure if any of the following hold:

- calibration intercept is nonfinite;
- calibration slope is nonfinite or nonpositive;
- `abs(intercept) > 0.25`;
- slope is outside `[0.50, 1.50]`.

This threshold is frozen pre-result and is intentionally a gross-miscalibration guard, not an optimization target.

## 8. Adverse-tail and concentration operationalization

For the frozen phrase `no material adverse tail`, require the 95% paired bootstrap upper bound on `candidate - null` CPL log loss to be less than `+0.005` in addition to bootstrap probability candidate-better `>=0.80`.

For concentration, report and require:

- at least 3 of 4 season point deltas non-adverse (`<=0`), as already preregistered;
- at least 3 of 4 leave-one-season-out aggregate deltas non-adverse;
- no single NFL week block contributes more than 50% of the total favorable aggregate paired-loss improvement when aggregate improvement is favorable;
- fixed favorite-size and total buckets are reported, and no sole bucket may be the only bucket with a favorable point delta when aggregate improvement is favorable.

These definitions are frozen before any candidate target score is generated.

## 9. ATS side decision and reference sensitivity

For descriptive ATS W-L-P only, choose the side with larger conditional non-push win probability. Ties at exactly 0.5 produce no directional decision.

`REFERENCE_MINUS110` uses unit risk 1.10 to win 1.00, excludes pushes from win/loss counts, and remains a sensitivity only. It is never a model-selection objective.

## 10. Result classification

If preflight fails: `FAILED`.

If preflight passes but aggregate primary paired CPL delta is `>=0`: `NO_MATERIAL_IMPROVEMENT` regardless of ATS hit rate or reference ROI.

Only if the aggregate delta is favorable may the remaining uncertainty, season, calibration, and concentration gates determine `HISTORICALLY_PROMISING` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`.
