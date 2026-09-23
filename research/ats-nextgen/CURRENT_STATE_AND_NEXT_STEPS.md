# ATS Next-Generation — Current State & Next Steps

## Current state

The prior Spread & Points Next-Generation program is complete. Its market-relative mean-margin and Candidate-5 hypotheses did not establish incremental value and are closed.

Phase 1 of this new ATS program has established a distinct scientific family centered on:

- market-relative conditional quantiles;
- discrete NFL margin probability mass;
- key-number/push modeling;
- heteroskedastic margin uncertainty;
- direct cover/push/loss probability estimation;
- exact wager economics when quoted prices exist.

The market is the primary null. Historical 2022–2025 results are development/non-pristine. Completed 2026 outcomes remain prohibited from candidate design and selection. No production code is changed.

## Frozen design summary

**Q1** estimates `R = M + L` at τ={10/21, 1/2, 11/21} using L1-regularized linear quantile regression and the compact frozen feature contract.

**Q2** builds `P(M=k)` for integer `k∈[-75,75]`, centered on the quoted market plus chronology-clean Q1 median residual, with conditional scale and training-only key-number excess at |margin|={3,6,7,10,14}. Generalized normal is the primary base; Gaussian, Student-t and empirical-residual forms are fixed comparisons, not an open model search.

**Q3** directly estimates cover/push/loss with a two-part hurdle: push probability on whole-number lines and conditional cover probability on non-push outcomes. Half-point lines have `P(push)=0` by construction.

A Q2/Q3 probability blend is authorized only on the fixed weight grid `{0, .25, .50, .75, 1}` using inner chronology-clean multinomial log loss.

## Exact Phase-2 starting action

After the final Phase-1 receipt is merged, create the Phase-2 research branch from the then-current `main`, read the complete Phase-1 package, and implement **data-contract/synthetic grading infrastructure plus Q1 only** before implementing Q2 or Q3. The first Phase-2 gate must prove sign convention, whole-/half-line grading, chronology, feature provenance and 2026-outcome exclusion before any candidate result is interpreted.

Phase 2 is not authorized to change production.