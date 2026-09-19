# LevLine Props 2.0 — Team Offensive TD Count Distribution Development Result

Status: **RETROSPECTIVE COMPONENT ISOLATION — REJECTED / CHALLENGER COLLAPSES TO POISSON**  
Workflow: `35418843763`  
Artifact: `10577161142`  
Contract: `levline-props-v2-team-td-count-v0.1.0`  
Production promotion authorized: **NO**

## Question

Does an overdispersed Gamma-Poisson / negative-binomial count model improve team offensive TD
uncertainty relative to Poisson when both models receive the exact same strictly lagged mean?

## Result

2023–2025 aggregate:
- N: **1,632 team-games / 816 games**;
- Poisson CRPS: **0.746728**;
- negative-binomial CRPS: **0.746728**;
- CRPS difference: **0.000000**;
- Poisson log loss: **1.710151**;
- negative-binomial log loss: **1.710151**;
- 80% coverage: **92.95%** for both.

The fitted overdispersion parameter was:
- 2023 evaluation, trained through 2022: **alpha = 0.0**;
- 2024 evaluation, trained through 2023: **alpha = 0.0**;
- 2025 evaluation, trained through 2024: **alpha = 0.0**.

Under the frozen parameterization, alpha=0 makes the negative-binomial distribution exactly Poisson.
Therefore every distributional score is identical and the advance gate fails with zero improving
seasons.

## Scientific disposition

**REJECT P2-TD-COUNT-V01.**

The data do not support generic team-level overdispersion beyond Poisson around this strictly lagged
mean. Do not force a positive alpha, tune the estimator, or search alternative dispersion floors
against these evaluated seasons.

This does **not** prove that all player touchdown models should be Poisson. Player-level scoring may
still benefit from better mean allocation, red-zone/goal-line opportunity modeling, or correlated
scoring state. It only rejects this generic team-count overdispersion mechanism as implemented.

No production model changes are authorized.
