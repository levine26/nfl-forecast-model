# ATS Joint-Score I-Projection V1 — Frozen Preregistration

**Candidate ID:** `ATS-JSIP-V1`  
**Status:** FROZEN BEFORE TARGET-SEASON SCORING  
**Program:** LevLine ATS / SpreadLine next-generation historical research  
**Production authorization:** NONE  
**Completed-2026 outcomes permitted:** 0

This document freezes the next primary challenger before any 2022–2025 target-season candidate score is generated. It is intentionally a single-mechanism experiment. No post-result rescue, architecture mutation, threshold search, or alternative candidate may be substituted under this candidate ID.

## 1. Scientific question

Does reconstructing a coherent **joint distribution of home and away final scores** from chronology-safe historical NFL scoring geometry, market spread/total state, and qualified paired-moneyline information improve ATS Cover/Push/Loss probability quality beyond the strongest canonical one-dimensional margin null, `KMASS-MARKETML-IPROJ`?

The hypothesis is specifically distributional. NFL scores are generated on a jagged integer lattice by football scoring increments. A joint score model can represent total-score state and score-pair geometry before it is marginalized to an exact integer-margin PMF. This is materially different from applying another smooth tilt to an already-constructed margin PMF.

## 2. Explicit novelty boundary versus prior candidates

This candidate is **not** a repair or rerun of `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`.

Q2 modeled `P(margin)` directly on frozen support `[-75,+75]`, starting from continuous margin families (`normal`, generalized normal, Student-t) discretized into integer cells and then applying margin-key adjustments. Q2 failed its frozen endpoint-mass gate before a complete accepted outer OOF score existed. `ATS-JSIP-V1` must not widen Q2 support, rerun Q2, reuse Q2's failed candidate outputs, or claim a Q2 result that does not exist.

`ATS-JSIP-V1` instead models `P(home_score, away_score)` on nonnegative integer score pairs, uses the market total as a first-class state variable in the score-generating location, applies the qualified moneyline constraint in score-pair space, and only then marginalizes to `P(home_margin)` and CPL probabilities.

It is also distinct from ATS Market Manifold V2. V2 preserved the one-dimensional null's sign totals and attempted smooth within-sign shape tilts. That mechanism is canonically rejected and is not reintroduced here.

## 3. Historical evidence boundary

Primary outer target seasons are fixed at:

`2022, 2023, 2024, 2025`.

Training/development data may use seasons `2015` through `S-1` for outer target season `S`, subject to the existing chronology and eligibility gates. Any inner-model or nuisance selection for outer season `S` must use only validation seasons strictly before `S`.

The 2022–2025 sample is non-pristine development evidence. A favorable historical result can justify prospective shadow evaluation only; it cannot authorize production.

Completed-2026 game outcomes, graded 2026 ATS results, 2026 candidate performance, or any feature derived from completed-2026 outcomes are forbidden.

## 4. Qualified inputs

### Mandatory

- sportsbook home spread `L`;
- spread-derived market home-margin center `C = -L` under the canonical sign contract;
- observed game identity / season / week needed for chronology and scoring.

### Optional, only when historically populated under the accepted archive semantics

- market total `T`;
- paired home/away moneylines converted to vig-free conditional non-tie home-win probability `u_market` using the repository's already-qualified paired-moneyline procedure.

Historical spread-side juice is **not qualified** and must not be invented. No missing price becomes `-110`. The historical spread/total archive remains exact-horizon opaque and must not be relabeled T-120, close, consensus, or constituent-book data beyond its established provenance.

Rows missing `T` remain eligible only for the preregistered total-missing fallback in Section 6. Rows missing a qualified paired moneyline receive no ML constraint; missing ML is never imputed from the final result or from assumed spread juice.

## 5. Score-space representation

The candidate state is a joint nonnegative integer grid `(H,A)` where `H` is home final score and `A` is away final score.

Numerical support is **adaptive, not hard-folded**:

1. begin with team-score support `0..80`;
2. construct the unnormalized base score marginals described below;
3. if estimated omitted upper-tail mass for either team exceeds `1e-12`, expand both score axes by 20 points and recompute;
4. repeat until each omitted upper tail is `<1e-12`;
5. never fold omitted mass into the endpoint.

Any row requiring support above 160, producing nonfinite probabilities, or failing normalization/constraint tolerances fails closed and is reported. This numerical guard is not a target-result tuning parameter.

## 6. Base joint score prior

For outer target season `S`, all nuisance quantities are trained strictly on seasons `<S`.

### 6.1 Market-implied score locations

When total `T` is present:

- `mu_H = (T + C) / 2`
- `mu_A = (T - C) / 2`

These are model location parameters, **not claims that sportsbook lines are exact mathematical expectations**.

When `T` is missing, use the median historical total from the outer training fold only, `T_train_median`, and set a `total_missing` diagnostic flag. The fallback value is never computed using target-season outcomes.

### 6.2 Structural single-team score kernel

Each team score marginal begins from a discretized Student-t location-scale kernel on nonnegative integer scores. The common degrees of freedom and scale are nuisance parameters selected only from prior inner validation seasons using observed-cell score log loss.

Frozen grids:

- `df ∈ {4, 6, 10}`;
- `scale ∈ {8, 10, 12, 14}` points.

Exact ties choose the simpler/heavier-regularized pair in this order: larger `df`, then larger `scale`.

### 6.3 Football score-lattice multiplier

To let the prior represent recurring NFL score cells without hand-picking post-result key scores, estimate a **league-wide single-team score-cell multiplier** from the outer training fold only.

For each integer team score `s`, compare its empirical training-fold frequency with its aggregate probability under the selected Student-t kernel evaluated at that row's market-implied team-score location. Apply symmetric Dirichlet shrinkage before forming the ratio.

Frozen total pseudocount grid:

`alpha ∈ {25, 100, 400}`.

Select `alpha` by pooled prior-season inner validation observed-cell score log loss only. Exact ties choose the larger pseudocount. No score value receives a manually added post-result bonus. For score cells absent from the training fold, shrinkage keeps the multiplier finite and positive.

The resulting home and away marginal kernels are normalized on the adaptive support. The unprojected joint prior is their product. V1 includes **no separately fitted score-correlation parameter**; correlation is introduced only through the qualified market win constraint below. This keeps the first test identifiable and prevents architecture sprawl.

## 7. Moneyline information projection

When qualified paired-moneyline probability `u_market` exists, update the joint prior `q(H,A)` by the minimum-KL / information-projection solution that changes `q` as little as possible subject to:

`P(H>A | H!=A) = u_market`.

Tie probability `P(H=A)` is preserved by the projection. Equivalently, positive-margin and negative-margin score-pair cells are rescaled to the qualified non-tie market win masses while all relative probabilities **within each sign region remain those of the joint score prior**.

This is the same qualified market-information semantic class already accepted by the canonical `KMASS-MARKETML-IPROJ` null, but applied to a genuinely different joint score prior.

When paired moneyline is unavailable, the candidate remains the unprojected joint score prior and the missing-ML flag is reported. No synthetic ML probability is generated from spread juice.

## 8. Margin and ATS probabilities

After the optional ML I-projection, marginalize exactly:

`P(M=m) = sum_{H-A=m} P(H,A)`.

For sportsbook home spread `L`, define home ATS outcome from `M + L` under the repository's canonical grading convention:

- Cover if `M + L > 0`;
- Push if `M + L = 0`;
- Loss if `M + L < 0`.

Half-point spreads therefore have zero push mass. Whole-number spreads retain the exact corresponding margin-cell push mass.

## 9. Chronological nuisance selection

For outer target season `S`, choose `(df, scale, alpha)` using expanding rolling-origin validation seasons strictly `<S`. Each inner validation season is forecast only from still-earlier training seasons. Pool the preregistered inner observed-cell score log loss across available prior validation rows.

No target-season candidate result, ATS grade, CPL score, hit rate, or ROI may influence nuisance selection.

If an outer season lacks sufficient prior evidence for the full selection protocol, fail closed rather than invent a fallback. The implementation must register the minimum-row requirement before any target-season scoring; it may not be chosen from target performance.

## 10. Required nulls

Primary null: `KMASS-MARKETML-IPROJ`, reproduced on the exact canonical common rows and under the existing accepted nuisance freeze.

Also report the existing market-only null hierarchy where mechanically available (`M0`, `M1`, `M2`) for continuity with the ATS Next-Generation evaluation protocol. These are diagnostics; they do not replace the primary null.

The candidate may not be compared to a weakened substitute simply because a stronger null is difficult to reproduce.

## 11. Primary and secondary metrics

### Primary selector

**Multinomial Cover/Push/Loss (CPL) log loss** on exact common eligible rows, candidate minus `KMASS-MARKETML-IPROJ`. Lower is better; a negative paired delta favors the candidate.

### Secondary, non-selective diagnostics

- CPL multiclass Brier;
- conditional non-push cover Brier and log loss;
- integer-margin observed-cell log score;
- discrete ranked probability / CRPS-style score;
- calibration intercept/slope where estimable;
- reliability/resolution/sharpness;
- expected/median margin error;
- push calibration overall and in the already-frozen key-number buckets;
- ATS W-L-P and non-push hit rate;
- per-season deltas;
- leave-one-season-out and leave-one-week robustness;
- fixed favorite-size and market-total diagnostic buckets from `research/ats-nextgen/EVALUATION_PROTOCOL.md`.

Historical ROI under assumed `-110` may appear only as the existing explicitly labeled `REFERENCE_MINUS110` sensitivity. It is not an actual quoted-price result and is not a selection metric.

## 12. Uncertainty

Use exact common rows and paired differences.

Final evidence uses 10,000 season-stratified NFL-week block bootstrap resamples with fixed seed `20260924`.

Report the paired 95% percentile interval and bootstrap probability that candidate CPL log loss is lower than the primary null. No alternative resampling scheme may be substituted after inspecting target results.

## 13. Advancement gate

`ATS-JSIP-V1` may be labeled `HISTORICALLY_PROMISING` only if all of the following hold:

1. aggregate primary CPL delta versus `KMASS-MARKETML-IPROJ` is strictly favorable;
2. paired 95% bootstrap interval does not show a material adverse tail and bootstrap probability candidate-better is at least `0.80`;
3. at least 3 of 4 outer seasons have non-adverse CPL point deltas;
4. no normalization, support, chronology, identity, or leakage failure occurs;
5. calibration does not show a material systematic failure;
6. the aggregate improvement is not solely explained by one season, week, or preregistered diagnostic bucket.

`ELIGIBLE_FOR_PROSPECTIVE_SHADOW` additionally requires repository research validation and firewall checks to pass on the exact accepted head. Historical evidence alone never authorizes production.

If the aggregate primary CPL delta is non-favorable, classification is `NO_MATERIAL_IMPROVEMENT` regardless of ATS hit rate or ROI. Structural/numerical invalidity is `FAILED` and is preserved as such; V1 is not repaired after seeing results.

## 14. Mandatory preflight invariants before target scoring

The implementation phase must prove, before generating any target-season candidate score:

1. no completed-2026 outcomes enter any frame;
2. all nuisance fits for target season `S` use seasons `<S` only;
3. mutating target `actual_margin`, final home score, final away score, or ATS grade does not change forecast probabilities;
4. all joint PMFs are finite, nonnegative, and sum to one within `5e-11`;
5. adaptive omitted upper-tail mass is `<1e-12` per team marginal with no endpoint folding;
6. ML projection preserves tie mass within `1e-12` and matches qualified conditional non-tie `u_market` within `2e-11`;
7. half-point spread push probability is exactly zero within numerical tolerance;
8. whole-number spread push probability equals the appropriate marginalized margin cell;
9. canonical primary-null row identities and hashes reproduce before candidate scoring;
10. production/protected surfaces are unchanged.

If any invariant fails, historical target scoring must fail closed.

## 15. Explicitly forbidden V1 mutations

After this freeze, do not:

- widen/rebuild Q2 and call it this candidate;
- add a football-feature residual learner;
- add QB/injury/personnel state;
- add score-pair correlation parameters;
- search alternative score keys or hand-tune lattice bonuses;
- add spread-bucket or total-bucket gating;
- optimize for ATS hit rate or ROI;
- assume historical spread price is `-110` for probability construction;
- inspect completed-2026 outcomes;
- alter production F-ST / LevLine / Sunday Signal behavior.

A scientifically justified extension requires a new candidate ID and a new preregistration after V1 is closed.

## 16. Next phase boundary

The next phase may implement the frozen machinery, tests, research-only workflow, and chronological 2022–2025 evaluation exactly as specified here. The preregistration commit must remain identifiable as the controlling pre-result commit. No target-season candidate scores may be generated on a commit earlier than or inconsistent with this frozen contract.
