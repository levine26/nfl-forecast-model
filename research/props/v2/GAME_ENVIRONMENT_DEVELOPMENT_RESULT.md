# LevLine Props 2.0 — Game Environment Residual Development Result

Status: **RETROSPECTIVE COMPONENT STUDY — REJECTED**  
Workflow: `35417908900`  
Artifact: `10576338704`  
Contract: `levline-props-v2-game-environment-v0.1.0`  
Production promotion authorized: **NO**

## Frozen question

Does pregame sportsbook OPEN game environment improve the existing top-level opportunity engine before
any player-prop integration?

The frozen challenger used low-dimensional ridge residuals on:
- team plays: game total, absolute team spread, opponent baseline predicted plays;
- dropback-logit: signed team spread, game total, absolute team spread.

No player-prop outcome was used.

## Aggregate result

2023–2025, **1,422 team-game rows / 711 games**:

- baseline team-plays MAE: **6.87917**
- challenger team-plays MAE: **6.91492**
- challenger minus baseline: **+0.03574 plays** (worse)
- game-clustered 95% interval: **+0.01396 to +0.05730**

- baseline dropback-rate MAE: **0.082411**
- challenger dropback-rate MAE: **0.082700**
- challenger minus baseline: **+0.000289** (worse)
- game-clustered 95% interval: **−0.000436 to +0.001018**

The primary team-play gate fails clearly: the entire clustered interval is above zero.

## By season

| Season | N | Δ team-play MAE | 95% CI | Δ dropback MAE |
|---|---:|---:|---:|---:|
| 2023 | 470 | **+0.08888** | +0.02634 to +0.14903 | +0.001546 |
| 2024 | 476 | **+0.00731** | −0.01037 to +0.02601 | −0.000572 |
| 2025 | 476 | **+0.01172** | −0.00233 to +0.02578 | −0.000090 |

Team-play MAE worsened in all three seasons. Small 2024/2025 dropback-rate improvements do not rescue
the candidate because the preregistered primary team-play criterion fails.

## Scientific disposition

**REJECT P2-GAME-ENV-V01 AS IMPLEMENTED.**

Do not tune ridge strength, feature combinations, sportsbook, or thresholds against these evaluated
outcomes. The fact that game total/spread are informative market variables in general does not mean
this frozen residual formulation improves LevLine's existing one-step-ahead team opportunity model.

Any future game-environment idea must be a new preregistered hypothesis with a distinct untouched
evaluation path. This result does not alter Props V1, F-ST, Sunday Signal, or production code.
