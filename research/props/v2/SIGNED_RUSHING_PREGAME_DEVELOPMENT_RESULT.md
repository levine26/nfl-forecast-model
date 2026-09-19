# LevLine Props 2.0 — Signed Rushing True-Pregame Development Result

Status: **RETROSPECTIVE PAIRED PREGAME ABLATION — REJECTED**  
Primary workflow: `35420676818`  
Contract: `levline-props-v2-signed-rushing-pregame-v0.1.0`  
Production promotion authorized: **NO**

## Question

The conditional event-level study showed that signed rushing-yard support improved CRPS when actual
event count was held fixed. This follow-up tested whether that mechanism improves the **full pregame
rushing-yard distribution** when V1's simulated carry counts are preserved exactly.

For every paired forecast:
- V1 pregame state is unchanged;
- sampled carry arrays are byte-for-byte identical;
- V1 rushing yards/carry mean and uncertainty are preserved;
- only the conditional rushing-yard draw changes from the nonnegative Gamma aggregate to centered
  signed empirical event residuals fitted through season S−1;
- target-game carries and target-game yards are not used in the fit.

## Aggregate result

2023–2025:
- N: **982** rushing-yard props;
- unique games: **230**;
- unique players: **114**;
- V1 CRPS: **18.26136**;
- signed-rushing CRPS: **18.30030**;
- challenger minus V1 CRPS: **+0.03894** (worse);
- game-clustered 95% interval: **+0.01676 to +0.06300**;
- V1 Fair-Line MAE: **24.90733**;
- signed-rushing Fair-Line MAE: **24.93737**;
- challenger minus V1 MAE: **+0.03004** (worse);
- game-clustered MAE-difference interval: **−0.02264 to +0.08299**;
- V1 80% coverage: **62.22%**;
- challenger 80% coverage: **63.14%**.

Coverage improves by about **+0.92 pp**, but the primary CRPS criterion fails clearly and Fair-Line
MAE also moves in the wrong direction.

## By season

| Season | N | Δ CRPS | Δ Fair-Line MAE | V1 80% cov. | Challenger 80% cov. |
|---|---:|---:|---:|---:|---:|
| 2023 | 279 | **+0.08908** | **+0.11470** | 56.27% | 58.06% |
| 2024 | 628 | **+0.02573** | −0.00239 | 64.65% | 65.29% |
| 2025* | 75 | −0.03703 | −0.01333 | 64.00% | 64.00% |

Only 2025 improves CRPS, and that genuine-OPEN slice is very small. The preregistered requirement
was improvement in at least two of three seasons.

## Scientific interpretation

The earlier signed-event component result was real but **does not survive composition with the
pregame carry-count distribution and V1 player mean**.

This is an important negative result: structural realism at the event level is not sufficient by
itself to improve the full player-prop distribution. The residual resampling broadens/reshapes the
aggregate in a way that slightly improves coverage but worsens probabilistic accuracy.

## Disposition

**REJECT P2-DIST-RUSH-PREGAME-V01.**

Do not:
- tune residual centering, pooling thresholds, tail clipping, or event sampling against these
  evaluated outcomes;
- rescue the candidate using the small 2025 slice;
- promote signed event support into production merely because the conditional component test passed.

The conditional signed-rushing mechanism remains useful scientific evidence about support
misspecification, but this specific pregame implementation fails its frozen gate.

No F-ST, Props V1, Sunday Signal, threshold, or production change is authorized.

*2025 genuine-OPEN evidence is a small sample.
