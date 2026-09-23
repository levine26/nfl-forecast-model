# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**. The prior Spread & Points Next-Generation program remains fixed negative evidence; its market-relative mean-margin and Candidate-5 hypotheses are closed and are not reopened here.

The ATS Next-Generation program has now frozen a distinct scientific family centered on:

- market-relative conditional quantiles;
- discrete NFL margin probability mass;
- key-number/push modeling;
- heteroskedastic margin uncertainty;
- direct cover/push/loss probability estimation;
- exact wager economics when quoted prices exist.

The market is the primary null. Historical 2022–2025 results are development/non-pristine. Completed 2026 outcomes remain prohibited from candidate design and selection. No production forecasting behavior was changed.

Phase-1 primary PR `#556` was validated on exact head `c1397729b7f973169ef6fda700f481a91ad25538` and merged at `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`. Research validation, research firewall, and the pull-request full test/model-refresh workflow all concluded successfully before merge.

## Frozen design summary

**Q1** — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` estimates `R = M + L` at τ={10/21, 1/2, 11/21} using L1-regularized linear quantile regression and the compact frozen feature contract.

**Q2** — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` builds `P(M=k)` for integer `k∈[-75,75]`, centered on the quoted market plus chronology-clean Q1 median residual, with conditional scale and training-only key-number excess at |margin|={3,6,7,10,14}. Generalized normal is the primary base; Gaussian, Student-t and empirical-residual forms are fixed comparisons, not an open model search.

**Q3** — `ATS-Q3-DIRECT-CPL-HURDLE-V1` directly estimates cover/push/loss with a two-part L2-logistic hurdle: push probability on whole-number lines and conditional cover probability on non-push outcomes. Half-point lines have `P(push)=0` by construction.

A Q2/Q3 probability blend is authorized only on the fixed weight grid `{0, .25, .50, .75, 1}` using inner chronology-clean multinomial log loss.

## Evidence boundary

Historical 2022–2025 evidence may be used only as development/non-pristine evidence for this ATS family. It may support mechanism testing, chronology-clean OOF comparison, calibration diagnostics and candidate rejection, but cannot by itself authorize production.

Completed 2026 outcomes remain firewalled from architecture, features, distribution choice, key-number choices, learner selection, threshold selection, calibration, blend selection and rescue. Outcome-blind prospective 2026 market/input data may be used only for source qualification.

## Exact Phase-2 starting action

Phase 2 is **NOT STARTED**.

When Phase 2 is explicitly begun, create a dedicated research branch from the then-current `main`, read the complete Phase-1 package, and implement **data-contract/synthetic grading infrastructure plus Q1 only** before implementing Q2 or Q3. The opening gate must prove:

- canonical home-spread sign convention and ATS grading;
- whole-number and half-point push logic;
- expanding-window chronology and no random K-fold;
- row-level feature/market provenance;
- exclusion of completed 2026 outcomes;
- pre-result code/config digests and opening receipt.

Only after those gates pass may Q1 historical development run. Phase 2 remains research-only and is not authorized to change production.