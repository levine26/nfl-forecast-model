# LevLine Props 2.0 — Defensive Efficiency Residual Development Result

Status: **RETROSPECTIVE COMPONENT ISOLATION — BOTH EVENT-TYPE GATES PASSED**  
Workflow: `35418742120`  
Artifact: `10576851625`  
Contract: `levline-props-v2-defensive-efficiency-v0.1.0`  
Production promotion authorized: **NO**

## Question

Does strictly lagged opponent defensive efficiency improve conditional rushing and receiving yardage
beyond the player's own shrunk efficiency baseline?

Rushing and receiving were preregistered as independent hypotheses. Actual event count was held fixed
to isolate the conditional efficiency mechanism, so this is **not a pregame prop forecast**.

## Receiving

2023–2025:
- N: **11,492** player-games;
- unique games: **816**;
- unique players: **681**;
- baseline conditional total-yard MAE: **12.08785**;
- challenger MAE: **11.89335**;
- improvement: **−0.19450**;
- game-clustered 95% interval: **−0.22350 to −0.16535**;
- baseline efficiency MAE: **4.89756 yards/reception**;
- challenger efficiency MAE: **4.82360**.

Season-level total-yard MAE improvement:
- 2023: **−0.23702**;
- 2024: **−0.18230**;
- 2025: **−0.16331**.

The receiving gate passes all frozen criteria.

## Rushing

2023–2025:
- N: **6,690** player-games;
- unique games: **816**;
- unique players: **520**;
- baseline conditional total-yard MAE: **11.02170**;
- challenger MAE: **10.89129**;
- improvement: **−0.13041**;
- game-clustered 95% interval: **−0.16407 to −0.09864**;
- baseline efficiency MAE: **2.58885 yards/carry**;
- challenger efficiency MAE: **2.56122**.

Season-level total-yard MAE improvement:
- 2023: **−0.15479**;
- 2024: **−0.10902**;
- 2025: **−0.12722**.

The rushing gate passes all frozen criteria.

## Mechanism

The fitted opponent-defense residual coefficient remains directionally stable season-forward.

Receiving standardized coefficient:
- fit through 2022: **0.2015**;
- fit through 2023: **0.2291**;
- fit through 2024: **0.2055**.

Rushing standardized coefficient:
- fit through 2022: **0.1001**;
- fit through 2023: **0.1088**;
- fit through 2024: **0.1004**.

This stability is more important than any single season point estimate.

## Scientific disposition

**ADVANCE BOTH RUSHING AND RECEIVING DEFENSIVE-EFFICIENCY RESIDUALS TO A TRUE PREGAME SIMULATOR ABLATION.**

Do not call these prop-accuracy gains. The study conditions on actual event count and therefore
cannot establish Fair-Line, cover, calibration, or betting improvement.

The next experiment should keep the existing V1 opportunity distribution intact and insert only the
strictly lagged defensive-efficiency residual into the rushing-yards/carry and
receiving-yards/reception means, then evaluate the full pregame distributions with CRPS, Fair-Line
MAE, calibration/coverage, and market-relative direction.

No production forecast, F-ST model, Props V1 output, or market threshold changes from this result.
