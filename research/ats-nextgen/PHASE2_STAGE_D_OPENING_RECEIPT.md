# ATS Next-Generation Phase 2 — Stage D Opening Receipt

**Status:** FROZEN BEFORE STAGE-D UNCERTAINTY EXECUTION  
**Program:** `LEVLINE_ATS_NEXTGEN`  
**Stage:** D — final evidence synthesis and uncertainty  
**Stage-C verified merge base:** `539081c59e62a5d4dbc0a8f849d8a332424ea06e`  
**Production control:** `F-ST-01-FROZEN-2026` — unchanged

## Scope

Stage D is evidence synthesis only. It may not train, retune, recalibrate, rescue, replace, blend, or otherwise modify Q1, Q2, or Q3. Completed-2026 outcomes remain prohibited. No production forecast or Sunday Signal numerical behavior may change.

## Admissible evidence

Only the already accepted Phase-2 evidence may be used:

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`, classified `VALID_NEGATIVE_INCREMENTAL_RESULT`; accepted OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`.
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`, classified `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT`; no accepted OOF artifact and no accepted primary performance result.
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1`, classified `NOT_INCREMENTAL_VS_Q3_M2`; accepted OOF SHA-256 `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`.
- Phase-2 historical gate identity remains `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`.

Q2 complementarity and Q2/Q3 blend cells are **unavailable**. Stage D must not reconstruct Q2, widen its support, substitute a different distribution, or manufacture a replacement blend.

## Reproducibility gate

Stage D must regenerate Q1 and Q3 using their frozen runners and refuse synthesis unless the regenerated OOF files exactly match the accepted SHA-256 identities above. This is a reproducibility operation, not a new candidate execution or selection round.

## Frozen uncertainty design

- paired resampling unit: the full `(season, week)` block;
- target seasons: exactly 2022–2025;
- bootstrap draws: exactly **10,000**;
- deterministic RNG seed: **26**;
- interval: percentile 95% interval (`alpha=0.05`);
- every delta is candidate minus its matching market-only null on exact paired rows;
- lower is better for every bootstrapped loss delta;
- `probability_better` is the fraction of bootstrap deltas `< 0`;
- no alternative block definition, seed search, subset search, threshold search, or multiple-run cherry-picking is allowed.

### Q1 primary paired loss

For each game and each frozen quantile `tau in {10/21, 1/2, 11/21}`, compute standard pinball loss on `ats_residual`. The per-game Q1 primary loss is the arithmetic mean of the three quantile pinball losses. Bootstrap the mean per-game difference `Q1 - M2`.

### Q3 primary paired loss

For each game, compute the frozen three-class cover/push/loss multinomial log loss. Bootstrap the mean per-game difference `Q3 - Q3_M2`.

### Q3 secondary paired loss

On non-push rows only, compute conditional-cover Brier loss from `P(cover)/(P(cover)+P(loss))`; bootstrap `Q3 - Q3_M2` using the same sampled `(season, week)` blocks and the sampled non-push rows within those blocks.

### Simple ATS hit-rate diagnostic

For each Q3 arm, on non-push rows classify home cover when conditional cover probability is `>= 0.5`. Report the observed hit rate and an exact two-sided 95% Clopper-Pearson interval. This diagnostic cannot select or rescue a candidate.

## Fixed reporting only

Stage D must carry forward the preregistered per-season and fixed-slice evidence already produced by Q1/Q3. It must not invent new slices. Historical side-price/juice provenance is not sufficient for a new ROI/EV claim; Stage D must not synthesize juice or use ATS/ROI to overturn the proper-score conclusions.

## Decision boundary

Stage D does not make the Phase-3 architecture classification itself. It produces the final Phase-2 evidence package and a Phase-3 handoff. The already observed Q1/Q2/Q3 outcomes remain evidence regardless of whether the uncertainty intervals include zero.
