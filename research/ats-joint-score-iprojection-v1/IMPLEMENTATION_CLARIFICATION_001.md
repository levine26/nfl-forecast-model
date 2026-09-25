# ATS-JSIP-V1 — Implementation Clarification 001

**Status:** PRE-TARGET-SCORING IMPLEMENTATION CLARIFICATION  
**Candidate:** `ATS-JSIP-V1`  
**Controlling preregistration commits:** `930320c94ffc1d554f72589328b48a98a3373662`, `f67cd216b73ee1861e8019c2eb6553438c3aeb64`  
**Novelty/readiness commit:** `50264684a74b34dbb1d9fa3b4c6c4455c6e111d3`  
**Target candidate scores inspected before this clarification:** 0  
**Completed-2026 outcomes used:** 0

This note resolves one numerical implementation detail that the frozen preregistration necessarily left implicit. It does **not** change any candidate parameter, grid, tolerance, support ceiling, data boundary, null, metric, or advancement rule.

## Nonnegative Student-t discretization

For a team-score location `mu`, degrees of freedom `df`, and scale `sigma`, the structural single-team kernel is interpreted as a Student-t location-scale distribution discretized to nonnegative integer score cells. Integer score `s >= 0` corresponds to the interval `[s-0.5, s+0.5)`, conditional on the latent score being at least `-0.5`.

Thus the pre-lattice kernel cell probability is

`P(s-0.5 <= X < s+0.5) / P(X >= -0.5)`.

This is the ordinary half-integer discretization of a continuous location-scale kernel onto the nonnegative integer lattice and introduces no fitted degree of freedom.

## Omitted-upper-tail audit

The preregistration requires adaptive support `0..80`, expansion by 20, omitted upper-tail mass `<1e-12`, no endpoint folding, and fail-closed behavior for any row requiring support above 160.

The football lattice multiplier is defined only on represented integer score cells. Therefore the preregistered **estimated omitted upper-tail mass** is implemented as the conditional structural Student-t kernel mass above the represented final half-cell boundary:

`P(X >= B+0.5 | X >= -0.5)`

for support bound `B`.

This estimate is evaluated before any endpoint normalization and before any target-season scoring. It is intentionally conservative with respect to the numerical support question: no unrepresented tail probability is silently folded into the endpoint or declared zero merely because the active lattice multiplier has no cell beyond `B`.

At preflight, every allowed frozen `(df, scale)` pair is evaluated. A row can pass the support invariant only if its actually selected nuisance pair would satisfy the tolerance at or below 160. If **even the minimum omitted tail across the entire frozen nuisance grid** exceeds `1e-12` at 160, then no legal nuisance selection can make that row pass and the frozen V1 experiment must fail closed before target scoring.

## Scientific consequence

If the support invariant fails under the frozen grid and ceiling, the result is `FAILED`, exactly as preregistered. The experiment will not widen support above 160, relax `1e-12`, replace Student-t with another kernel, truncate/fold the tail, or select a nuisance pair based on target performance under the `ATS-JSIP-V1` ID.
