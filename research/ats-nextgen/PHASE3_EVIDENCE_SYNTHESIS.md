# ATS Next-Generation — Phase 3 Evidence Synthesis & Classification

**Program:** `LEVLINE_ATS_NEXTGEN`  
**Phase:** 3 — Scientific Synthesis, Candidate Selection & Freeze  
**Evidence source:** frozen Phase-2 receipts/registries and accepted artifacts only  
**Phase-3 opening base:** `a5c7bf6c37b9d1b385bfe88bd1a329ddd3bb63f0`  
**Production:** `F-ST-01-FROZEN-2026` — unchanged  
**Completed-2026 outcomes used:** `0`

## 1. Decision rule

The Phase-1 Evaluation Protocol allows `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` only when the frozen candidate improves its primary proper/quantile metric over the corresponding market null on exact common OOF rows, calibration does not materially fail, the improvement is not concentrated in a narrow time/key slice, no leakage/red-team failure exists, and the mechanism remains the preregistered architecture.

Phase 3 does not reinterpret ATS hit rate, ROI, favorable slices or a confidence interval crossing zero as a substitute for passing the primary incremental metric. A confidence interval crossing zero limits how strongly an adverse point estimate can be described as harmful; it does not turn a non-improving point estimate into a successful incremental result.

## 2. Candidate evidence table

| Candidate | Structural validity | Primary frozen comparison | Paired uncertainty | Supporting diagnostics | Evidence limitation | Phase-3 status |
|---|---|---|---|---|---|---|
| `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` | Valid chronology-clean V1 execution | Q1 − M2 mean-three-quantile pinball `+0.0001307887665715768` (lower is better; Q1 worse) | 95% CI `[-0.002378435765685505,+0.002555544033066125]`; P(Q1 better) `0.4554` | Better/equal/worse pinball in frozen slice×quantile cells: 12/14/16; season deltas: better 2022, equal 2023, worse 2024–2025; football block often shrunk to no change | 2022–2025 is development/non-pristine; tiny effect not precisely resolved | **REJECTED** |
| `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` | **Invalid under frozen V1 support contract** | No accepted Q2-vs-M1 primary proper-score comparison exists | Not applicable — complete valid Q2 OOF does not exist | Frozen support `[-75,+75]`; endpoint threshold `0.001`; observed max folded endpoint mass `0.0033487075822347966`; execution failed closed before complete OOF | Underlying wider-support concept was not validly tested and is not classified here | **REJECTED** |
| `ATS-Q3-DIRECT-CPL-HURDLE-V1` | Valid chronology-clean V1 execution | Q3 − Q3-M2 multinomial CPL log loss `+0.0013157418572419255` (lower is better; Q3 worse) | 95% CI `[-0.0015590942193462521,+0.004336647782633088]`; P(Q3 better) `0.1842` | Non-push Brier delta `+0.0006716459171549338`, P(better) `0.1851`; cover-calibration slope Q3 `0.27094382668690847` vs Q3-M2 `0.8130523437112027`; Q3 worse in 3/4 seasons and 10/14 frozen slices | 2022–2025 is development/non-pristine; tiny effect not precisely resolved | **REJECTED** |

## 3. Q1 classification — REJECTED

Q1 was a valid, chronology-clean experiment, but its frozen question was whether compact football state improved conditional quantile estimation beyond market-only M2. It did not.

The pooled primary delta is slightly adverse: `+0.0001307887665715768` pinball units, where lower is better. The paired block-bootstrap interval crosses zero, so the evidence does **not** establish a materially harmful Q1 effect. But Phase 3 is not a test of whether Q1 is definitely harmful; it is a survival test requiring evidence of incremental improvement. Q1 did not satisfy that gate.

The result is also not rescued by its internal heterogeneity. Q1 was better in 2022, equal in 2023, and worse in 2024 and 2025. Across the 42 frozen slice×quantile cells, Q1 pinball was better in 12, equal in 14, and worse in 16. Its low-quantile predictions were identical to M2 on all 1,087 OOF rows, and additional football state frequently shrank to no change.

**Classification:** `REJECTED` as the frozen V1 incremental architecture. This does not mean a large detrimental effect has been proven, and it does not prohibit a genuinely new future research program from studying a materially different architecture under a new preregistration.

**Reason code:** `FAILED_PRIMARY_INCREMENTAL_QUANTILE_GATE`.

## 4. Q2 classification — REJECTED

Q2 is not an ordinary underpowered or statistically inconclusive candidate. Its own frozen V1 numerical-support contract invalidated the experiment before a complete accepted OOF distribution/performance package could exist.

The preregistered PMF support was exactly `[-75,+75]`, with a material endpoint-mass threshold of `0.001`. During the first accepted historical execution, a preregistered generalized-normal candidate state produced maximum folded endpoint mass `0.0033487075822347966`, triggering the frozen fail-closed rule.

Accordingly there is no accepted Q2-vs-M1 discrete CRPS result, no complete valid Q2 OOF, no Q2 complementarity result, and no Q2/Q3 blend. Phase 3 may not widen support, relax the threshold, drop the failing arm, substitute a different distribution, or infer performance that was never validly measured.

**Classification:** `REJECTED` as `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` because V1 is structurally invalid under its frozen support/truncation contract. This classification does **not** conclude that a separately preregistered wider-support Q2 successor would fail; that is a different experiment and is outside this phase.

**Reason code:** `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT`.

## 5. Q3 classification — REJECTED

Q3 was a valid, chronology-clean direct cover/push/loss experiment. Its preregistration states explicitly that if Q3 proper scores fail against market-only Q3-M2, Q3 is rejected even if a realized betting subset appears favorable.

The primary multinomial CPL log-loss delta is adverse: `+0.0013157418572419255`, where lower is better. The paired 95% CI crosses zero, so the development evidence does not prove a large harmful effect. But the probability that the paired bootstrap delta favors Q3 is only `0.1842`, and the frozen point result fails the required positive incremental gate.

Supporting probability evidence is aligned with that conclusion: non-push Brier is worse by `+0.0006716459171549338`; Q3's conditional-cover calibration slope is `0.27094382668690847` versus `0.8130523437112027` for Q3-M2; Q3 is worse on primary log loss in three of four outer seasons and ten of fourteen frozen reporting slices. The simple non-push ATS hit-rate diagnostic also does not rescue it (`52.1739%` Q3 vs `52.8355%` Q3-M2).

**Classification:** `REJECTED` as the frozen V1 incremental architecture.

**Reason code:** `FAILED_PRIMARY_INCREMENTAL_PROPER_SCORE_GATE`.

## 6. Program-level selection result

Phase 3 produces **zero** candidates eligible for prospective shadow:

- Q1: `REJECTED`;
- Q2: `REJECTED`;
- Q3: `REJECTED`;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`: none;
- `INCONCLUSIVE`: none.

`INCONCLUSIVE` is not used merely because the Q1/Q3 uncertainty intervals cross zero. Those intervals show that effects of the observed tiny magnitude are not sharply resolved; however, both valid candidates failed the program's required positive primary-metric gate. Q2 is structurally invalid rather than statistically unresolved.

## 7. Consequences

No prospective-shadow specification is created because no candidate earned eligibility. Phase 4 therefore remains **NOT AUTHORIZED / NOT STARTED**. It cannot begin without a future program amendment or new eligible architecture plus explicit user authorization under the governing research process.

Production remains `F-ST-01-FROZEN-2026`; no Phase-3 classification changes Sunday Signal, F-ST coefficients, numerical forecasts, locks, grading, public fair-spread semantics or any production selection path.

## 8. Scientific interpretation

The Phase-2/Phase-3 evidence supports a narrow conclusion: under the frozen V1 formulations, the tested compact football-state additions did not demonstrate incremental probability/quantile information beyond the relevant market-only nulls, and the discrete Q2 V1 specification failed its own numerical-support contract.

This is not evidence that NFL forecasting cannot improve on markets, nor proof that Q1/Q3 are materially worse in a broader population. The development sample is non-pristine and the Q1/Q3 adverse effects are small with intervals crossing zero. The correct governance response is nevertheless to preserve the negative/invalid V1 results and stop, rather than rescue them after inspection.