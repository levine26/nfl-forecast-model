# Phase 3 Development Evaluation

## Scope

This report records the frozen 2022-2024 rolling-origin development evidence for Phase 3. It is not a 2025 holdout report. The exact validated source run was GitHub Actions run `35810171571` at head `3d893ec8e26824f7e6c1883f4d0d09c19160c712`.

- games: 815 regular-season games across 2022-2024
- implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`
- market label: `historical_closing_late_benchmark_exact_horizon_opaque`
- 2025 loaded/scored: **NO / NO**
- completed-2026 outcomes used for selection: **NO**
- Candidate 5 trained: **NO**

The durable machine-readable evidence is under `phase3/evidence/`.

## Pooled development results

| Model | Margin MAE | Total MAE | Home pts MAE | Away pts MAE | Winner accuracy | Brier | Log loss |
|---|---:|---:|---:|---:|---:|---:|---:|
| A0 | 9.883 | 10.387 | 7.527 | 7.203 | 62.945% | 0.2277 | 0.6471 |
| B0 | 10.213 | 11.304 | 7.731 | 7.753 | 60.491% | 0.2330 | 0.6580 |
| C0 M3 | 9.439 | 10.138 | — | — | — | — | — |
| Market M0 | 9.418 | 10.121 | — | — | — | — | — |
| Historical scoring average | 10.033 | 10.462 | — | — | — | — | — |
| Simple EPA/team strength | 9.807 | 10.578 | — | — | — | — | — |
| Naive HFA/league total | 10.597 | 10.804 | — | — | — | — | — |

Phase 1 F-ST winner accuracy (68.1693%) is retained only as context because the Phase 1 summary covers a different 2022-2025 evidence scope. It is not substituted into the exact paired Phase 3 2022-2024 comparisons.

## A0 — dynamic opponent-adjusted joint score

A0 is methodologically valid and survives as a Phase 4 reference. Its pooled margin MAE is 9.883 and total MAE is 10.387.

Against the exact paired market rows:

- margin: A0 is worse by **0.464 points MAE**; block-bootstrap 95% interval [0.274, 0.658]; P(A0 lower MAE) = 0.0000.
- total: A0 is worse by **0.266 points MAE**; block-bootstrap 95% interval [0.080, 0.455]; P(A0 lower MAE) = 0.0025.

Selected development hyperparameters were strongly regularized: alpha 100 in 2022-2024; half-life 4 in 2022/2023 and 8 in 2024. This is a result of the preregistered inner objective, not a post-result change.

A0 distribution calibration was broadly usable: 80% interval coverage was 81.35% for margin and 82.58% for total. The 50% intervals covered 56.20% and 54.97%, respectively.

## B0 — possession / drive score process

B0 is also methodologically valid and remains a Phase 4 reference, but it is the weakest pooled score candidate.

Against the exact paired market rows:

- margin: B0 is worse by **0.795 points MAE**; 95% block-bootstrap interval [0.495, 1.096].
- total: B0 is worse by **1.184 points MAE**; 95% block-bootstrap interval [0.847, 1.508].

B0 exhibits a material total-score underprediction bias: actual minus predicted total = **+4.200 points** pooled. No count-family or model-family rescue is authorized in Phase 3.

The empirical simulator was deliberately conservative/wide: 80% coverage was about 90.06% for margin and 92.02% for total. That sharpness/calibration tradeoff is preserved as a negative result.

## C0 — market residual hierarchy

The frozen null hierarchy gives:

| Arm | Margin MAE | Total MAE |
|---|---:|---:|
| M0 market only | **9.4184** | **10.1209** |
| M1 market + line calibration | 9.4345 | 10.1267 |
| M2 market + football residual information | 9.4386 | 10.1380 |
| M3 full C0 | 9.4390 | 10.1376 |

Disposition for both targets:

**NO_INCREMENTAL_FOOTBALL_EDGE**

For M3 versus M0:

- margin difference = +0.0206 MAE; 95% block-bootstrap interval [-0.0111, 0.0533]; P(M3 lower) = 0.1052.
- total difference = +0.0168 MAE; 95% block-bootstrap interval [-0.0113, 0.0451]; P(M3 lower) = 0.1197.

The residual correction therefore does not earn a historical development claim over the closing/late benchmark. This is the central Phase 3 negative result and is preserved without rescue tuning.

## D

D is **ENSEMBLE_NOT_ELIGIBLE** for margin and total. See `D_ELIGIBILITY_RECEIPT.md` and the machine-readable receipt.

## Interpretation

The 2022-2024 development evidence supports three conclusions without promoting any model:

1. simple and market baselines remain difficult to beat;
2. A0 provides a usable independent football representation but not a market-relative MAE improvement;
3. B0 adds a structurally different representation but loses materially on pooled score accuracy;
4. C0 shows that the frozen A0 football information does not explain enough residual closing/late market error to improve MAE.

These are development findings only. Phase 4, not Phase 3, owns the one-time 2025 underlying-model holdout.
