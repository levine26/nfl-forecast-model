# LevLine Props 2.0 — Signed Rushing True-Pregame Development Result

Status: **RETROSPECTIVE TRUE-PREGAME ABLATION — REJECTED**  
Primary workflow: `35420043916`  
Primary artifacts:
- 2023: `10576698018`
- 2024: `10577307344`
- 2025: `10577196966`
Contract: `levline-props-v2-signed-rushing-pregame-v0.1.0`  
Production promotion authorized: **NO**

## Question

The component-isolation study showed that signed empirical rushing-event support improved CRPS when
the realized carry count was held fixed.

This follow-up tested whether that mechanism improves a **true pregame rushing-yard distribution**
when V1's sampled carry uncertainty is restored and preserved exactly.

For every player-game:
- the frozen V1 pregame state was used;
- the exact V1 sampled carry array was preserved;
- V1 mean rushing yards/carry and mean uncertainty were preserved;
- only the conditional rushing-yard draw changed from nonnegative Gamma to centered signed empirical
  rushing-event residuals fitted through season S−1.

Target-game carries and target-game yards were not used for fitting or forecast construction.

## Aggregate result

2023–2025:
- N: **982** rushing-yard props;
- unique games: **230**;
- unique players: **114**;
- V1 CRPS: **18.26395**;
- challenger CRPS: **18.30303**;
- challenger minus V1 CRPS: **+0.03907** (worse);
- game-clustered 95% interval: **+0.01652 to +0.06379**;
- V1 Fair-Line MAE: **24.92210**;
- challenger Fair-Line MAE: **24.93534**;
- challenger minus V1 MAE: **+0.01324** (worse);
- game-clustered MAE-difference interval: **−0.04285 to +0.07040**;
- V1 80% coverage: **62.42%**;
- challenger 80% coverage: **63.24%**.

Coverage improves by approximately **+0.81 pp**, but this cannot rescue worse CRPS and Fair-Line MAE.

## By season

| Season | N | Δ CRPS | Δ Fair-Line MAE | V1 80% cov. | Challenger 80% cov. |
|---|---:|---:|---:|---:|---:|
| 2023 | 279 | **+0.08278** | **+0.09498** | 56.63% | 58.06% |
| 2024 | 628 | **+0.02813** | −0.01831 | 64.81% | 65.45% |
| 2025* | 75 | −0.03189 | −0.02667 | 64.00% | 64.00% |

*2025 is a small genuine-OPEN sample and cannot rescue the pooled failure.

CRPS improves in only **one of three seasons**.

## Frozen gate

- pooled CRPS improves: **FAIL**
- pooled Fair-Line MAE improves: **FAIL**
- at least two seasons improve CRPS: **FAIL**
- pooled clustered CRPS CI upper bound <= 0: **FAIL**
- coverage deterioration <= 1.5 pp: **PASS**

Overall gate: **FAIL**.

## Scientific disposition

**REJECT P2-DIST-RUSH-PREGAME-V01 AS IMPLEMENTED.**

The earlier component result was real but conditional on realized event count. Once pregame carry
uncertainty is restored, the signed empirical event-support overlay slightly degrades the full
rushing-yard predictive distribution.

Do not tune residual pools, minimum pool size, centering rule, support, or blending weight against
these evaluated outcomes. The correct inference is that signed support alone is not sufficient to
improve the current pregame rushing-yard model.

This result does not invalidate the component finding; it shows that the component gain does not
translate into a full pregame gain under the frozen V1 opportunity process.

No production forecast, F-ST model, Props V1 output, or market threshold changes from this result.
