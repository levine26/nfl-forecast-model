# LevLine Props 2.0 — Dynamic Role V2 Development Result

Status: **RETROSPECTIVE DEVELOPMENT — PREREGISTERED CANDIDATE REJECTED**  
Source workflow: `35417823424`  
Frozen contract: `levline-props-v2-dynamic-role-development-v0.2.0`  
Production promotion authorized: **NO**

## Experiment

Dynamic Role V2 replaced the V0.1 fixed short/long EWMA role proxy with a season-forward latent
random-walk state on logit offensive snap share.

State-transition parameters were estimated only from historical participation trajectories through
the prior season. No prop outcome, Fair-Line error, sportsbook result, cover result, or completed
2026 outcome entered the state fit.

Two ablations were frozen before primary outcome evaluation:

- `route_only`: latent participation state adjusts route-role level;
- `full`: route level plus posterior-vs-long-run target/carry trend.

Proper distribution metrics (empirical CRPS plus 80% interval score/coverage) were frozen before the
primary evaluation.

All six primary season/mode jobs completed successfully. The original aggregate job failed only
because GitHub artifact flattening combined same-named CSVs. The results below were reconstructed
directly from the six immutable primary artifacts; the workflow has been corrected to retain
per-artifact directories.

Canonical aggregate workflow completed successfully after the artifact-layout fix. Canonical aggregate artifact: `10577640488`.

Canonical aggregate workflow: `35417823424`  
Canonical aggregate artifact: `10577640488`

## Route-only V2

Paired decided props: **5,659**  
Unique games: **230**  
Unique players: **307**

- challenger accuracy: **50.96%**
- paired V1 accuracy: **51.03%**
- challenger minus V1: **−0.07 pp**
- game-clustered 95% interval for challenger-minus-V1: **−0.31 to +0.16 pp**
- sportsbook price-direction accuracy: **53.51%**
- challenger minus sportsbook direction: **−2.54 pp**
- game-clustered 95% interval versus sportsbook direction: **−4.44 to −0.56 pp**
- challenger Fair-Line MAE: **19.291**
- V1 Fair-Line MAE: **19.229**
- challenger minus V1 MAE: **+0.065** (worse)
- sportsbook line MAE: **15.973**
- challenger CRPS: **13.8983**
- V1 CRPS: **13.8461**
- challenger minus V1 CRPS: **+0.0522** (worse)
- challenger 80% interval score: **89.793**
- V1 80% interval score: **89.290**
- challenger 80% coverage: **73.03%**
- V1 80% coverage: **73.00%**

### Route-only by season

| Season | N | Δ accuracy | Challenger MAE | V1 MAE | Δ CRPS |
|---|---:|---:|---:|---:|---:|
| 2023 | 1,551 | +0.26 pp | 24.147 | 23.960 | +0.1721 |
| 2024 | 3,695 | −0.16 pp | 17.531 | 17.513 | +0.0091 |
| 2025* | 413 | −0.24 pp | 16.835 | 16.809 | +0.0015 |

*2025 genuine-OPEN evidence is a small 16-game sample.

## Full V2

Paired decided props: **5,659**  
Unique games: **230**  
Unique players: **307**

- challenger accuracy: **51.12%**
- paired V1 accuracy: **51.03%**
- challenger minus V1: **+0.09 pp**
- game-clustered 95% interval for challenger-minus-V1: **−0.95 to +1.15 pp**
- sportsbook price-direction accuracy: **53.51%**
- challenger minus sportsbook direction: **−2.42 pp**
- game-clustered 95% interval versus sportsbook direction: **−4.30 to −0.61 pp**
- challenger Fair-Line MAE: **19.820**
- V1 Fair-Line MAE: **19.233**
- challenger minus V1 MAE: **+0.587** (materially worse)
- sportsbook line MAE: **15.976**
- challenger CRPS: **14.3212**
- V1 CRPS: **13.8481**
- challenger minus V1 CRPS: **+0.4731** (materially worse)
- challenger 80% interval score: **92.931**
- V1 80% interval score: **89.297**
- challenger 80% coverage: **71.78%**
- V1 80% coverage: **73.00%**

### Full by season

| Season | N | Δ accuracy | Challenger MAE | V1 MAE | Δ CRPS |
|---|---:|---:|---:|---:|---:|
| 2023 | 1,550 | +0.26 pp | 24.995 | 23.973 | +0.8015 |
| 2024 | 3,696 | −0.16 pp | 17.963 | 17.515 | +0.3645 |
| 2025* | 413 | +1.21 pp | 17.006 | 16.809 | +0.2079 |

The favorable 2025 directional point estimate is not a rescue criterion. It is a small previously
inspected sample, while Fair-Line MAE and CRPS are worse in every season.

## Scientific disposition

**REJECT DYNAMIC ROLE V2 V0.2 AS IMPLEMENTED.**

The latent random-walk snap-state specification does not improve the football forecast distribution.
The full version materially degrades Fair-Line error, CRPS, interval score, and coverage. The
route-only version is much closer to V1 but still worsens MAE and CRPS and provides no directional
gain.

This is especially important because Dynamic Role V0.1 full had shown a modest, stable Fair-Line MAE
improvement. Greater state-space sophistication did **not** improve the model.

The appropriate conclusion is not to tune V2 against these outcomes. V0.1 remains the stronger
retrospective role hypothesis for eventual prospective testing. Any future role model must be a new
scientific candidate with a new preregistration and untouched evaluation path.
