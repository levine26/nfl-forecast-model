# LevLine Props 2.0 — Signed Rushing True-Pregame Development Result

Status: **RETROSPECTIVE TRUE-PREGAME ABLATION — REJECTED**  
Contract: `levline-props-v2-signed-rushing-pregame-v0.1.0`  
Production promotion authorized: **NO**

## Design

This follow-up took the positive signed-rushing event-support component result and removed the
postgame event-count conditioning.

For each historical player-game:
- the frozen V1 pregame state was built normally;
- V1's sampled carry array was preserved exactly;
- V1 mean rushing yards/carry was preserved;
- only the conditional rushing-yard event support was changed from nonnegative Gamma to signed
  empirical historical residuals;
- target-game carries and target-game yards were never used to fit or construct the forecast.

All three primary season jobs passed the isolation assertions.

Primary artifacts:
- 2023: `10577330985`;
- 2024: `10577865798`;
- 2025: `10577735587`.

The pooled statistics below were reproduced directly from those immutable primary CSVs using the
already-frozen aggregate code and bootstrap seeds while the GitHub aggregate job was still queued.

## Aggregate 2023–2025

N: **982 rushing-yard props**  
Unique games: **230**  
Unique players: **114**

- V1 CRPS: **18.26669**
- signed-rushing CRPS: **18.30423**
- challenger minus V1 CRPS: **+0.03754** (worse)
- game-clustered 95% CI: **+0.01576 to +0.06120**

- V1 Fair-Line MAE: **24.91395**
- signed-rushing Fair-Line MAE: **24.93737**
- challenger minus V1 MAE: **+0.02342** (worse)
- game-clustered 95% CI: **−0.03027 to +0.07641**

- V1 80% coverage: **62.32%**
- signed-rushing 80% coverage: **63.14%**
- V1 80% interval score: **121.818**
- signed-rushing 80% interval score: **122.665**

Directional accuracy, diagnostic only:
- V1: **49.19%**
- signed-rushing: **49.59%**

The small directional increase cannot rescue the failed proper-score gate.

## By season

| Season | N | Δ CRPS | CRPS 95% CI | Δ Fair-Line MAE |
|---|---:|---:|---:|---:|
| 2023 | 279 | **+0.08278** | +0.04213 to +0.12667 | +0.09498 |
| 2024 | 628 | **+0.02573** | −0.00140 to +0.05446 | −0.00239 |
| 2025* | 75 | **−0.03189** | −0.09541 to +0.03644 | −0.02667 |

*2025 is a very small genuine-OPEN sample.

Only one of three seasons improves CRPS.

## Frozen gate

The candidate fails:
1. pooled CRPS improves — **FAIL**;
2. pooled Fair-Line MAE improves — **FAIL**;
3. at least two of three seasons improve CRPS — **FAIL**;
4. pooled clustered CRPS CI upper bound <= 0 — **FAIL**;
5. coverage deterioration <= 1.5 pp — **PASS**.

## Scientific disposition

**REJECT P2-DIST-RUSH-PREGAME-V01.**

The earlier component result was real but did not survive integration with V1's pregame opportunity
uncertainty and player-specific efficiency means. Signed event support by itself is therefore not a
valid Props 2.0 improvement under this frozen construction.

Do not tune residual-pool scope, variance, position fallback, or mixture weights against these
evaluated outcomes. A future distributional candidate would need a substantively new preregistered
mechanism and untouched evaluation path.

No F-ST, Props V1, Sunday Signal, production threshold, or published forecast changes from this
result.
