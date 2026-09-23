# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**. PR #556 merged the exact-head validated ATS research/preregistration package at `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`. Q1/Q2/Q3 remain untrained. No candidate-specific ATS historical performance was generated in Phase 1. Production remains `F-ST-01-FROZEN-2026` and Sunday Signal numerical forecasting is unchanged.

The prior Spread & Points negative evidence remains closed. The new ATS family is scientifically distinct and frozen around:

- market-relative conditional quantiles;
- discrete NFL margin probability mass;
- key-number and push modeling;
- conditional margin dispersion;
- direct cover/push/loss probability estimation;
- exact side-price economics only when quoted price is genuinely available.

Historical 2022–2025 evidence is development/non-pristine. Completed 2026 outcomes remain prohibited from candidate design, fitting, tuning, selection, rescue, and historical survival decisions.

## Frozen design summary

**Q1** — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`: estimates `R=M+L` at τ={10/21,1/2,11/21} with L1-regularized linear quantile regression.

**Q2** — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`: produces an integer PMF on [-75,75], centered on the quoted market plus chronology-clean Q1 median residual, with bounded generalized-normal/Gaussian/Student-t/empirical comparisons, fixed conditional-scale terms and training-only key-number excess at |margin|={3,6,7,10,14}.

**Q3** — `ATS-Q3-DIRECT-CPL-HURDLE-V1`: two-part L2-logistic hurdle estimating push on whole-number lines and conditional cover on non-push rows, with half-point push probability structurally zero.

A Q2/Q3 blend is authorized only on `w_Q2={0,.25,.50,.75,1}` selected by inner chronology-clean multinomial log loss.

## Exact Phase-2 starting action

Phase 2 is **NOT STARTED**. When it is explicitly continued:

1. create a dedicated Phase-2 research branch from then-current `main`;
2. read the complete Phase-1 package and final receipt;
3. implement canonical sign/ATS grading helpers and the preregistered synthetic grading tests;
4. assert whole-/half-line push logic;
5. build row-level provenance for spread/total/moneyline and compact football state;
6. assert outer/inner rolling chronology and completed-2026 exclusion;
7. freeze implementation/config hashes in a pre-result Phase-2 opening receipt;
8. only then fit Q1; implement Q2 and Q3 later in the frozen sequence.

Phase 2 remains research-only and is not authorized to change production.
