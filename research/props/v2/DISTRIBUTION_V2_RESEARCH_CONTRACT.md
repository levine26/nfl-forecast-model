# Props 2.0 Distribution / Simulation V2 — Event Distribution Contract

Status: **PREREGISTERED MECHANISM STUDY**  
Candidate: `P2-DIST-V2`  
Version: `levline-props-v2-event-distribution-v0.1.0`

## Problem

The current compound-Gamma yardage function is nonnegative by construction. NFL rushing and
receiving events can lose yards. Before changing the coherent simulator, test whether a
support-correct event family materially improves out-of-sample distribution quality when both
families receive the same historical population.

## Frozen comparison

For each eligible event kind × position:
- **baseline:** moment-matched nonnegative Gamma;
- **candidate:** 90% position empirical bootstrap + 10% same-event-kind league bootstrap.

The candidate is deliberately low-dimensional. It is not allowed to select mixture weights from
2024/2025 prop outcomes. The 90/10 shrinkage is frozen before evaluation.

Rolling chronology:
- train 2021–2023 → test 2024;
- train 2021–2024 → test 2025.

No random shuffle.

## Event populations

- rushing: official rushing attempts with stable QB/RB/WR/TE identity and observed rushing yards;
- receiving: completed passes with stable receiver identity and observed receiving yards.

This first study isolates distribution support/shape. It does not claim contextual efficiency or
player skill improvement.

## Metrics

- CRPS from a fixed Monte Carlo representation;
- categorical log loss and multiclass Brier on structural yard bins;
- 50% and 90% interval coverage;
- negative-event prevalence;
- season/kind/position cells plus weighted aggregate.

## Promotion boundary

A support-correct family may proceed to a coherent simulator challenger only if:
- aggregate CRPS improves;
- categorical proper scores do not materially degrade;
- improvement is not solely one tiny subgroup;
- negative-event support is preserved;
- chronology/source checks pass.

Passing does not authorize production. A subsequent player-prop simulation backtest is required.

## Governance

No completed 2026 outcomes. No sportsbook data. No edge thresholds. No production changes.
