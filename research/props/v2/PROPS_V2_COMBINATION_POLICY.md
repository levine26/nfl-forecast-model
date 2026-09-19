# LevLine Props 2.0 — Mechanism Combination Policy

Status: **FROZEN BEFORE DEFENSIVE-EFFICIENCY PREGAME RESULTS ARE COMPLETE**  
Date: 2026-09-19

## Purpose

Prevent repeated retrospective combination searches from turning individually tested football
mechanisms into an overfit "best-of" Props 2.0 model.

## Rule

The 2023–2025 historical prop population has already been used extensively for V1 development and
multiple Props 2.0 component experiments. It may be used to **reject** preregistered mechanisms and
to determine whether a mechanism earns prospective shadow status, but it will not be used to search
arbitrarily across combinations of previously inspected mechanisms.

## Mechanism ladder

A mechanism can advance through these stages:

1. **Football-process/component isolation**
   - no prop-cover tuning;
   - establishes whether the mechanism improves the football quantity it claims to model.

2. **True pregame paired ablation**
   - all unrelated V1 inputs/distributions remain fixed;
   - the mechanism must pass its preregistered proper-score/Fair-Line gate.

3. **Prospective shadow eligibility**
   - passing a retrospective pregame gate does not authorize production;
   - the mechanism is frozen before future outcomes and market movement are observed.

4. **Prospective combined challenger**
   - may contain only mechanisms that independently passed their own true-pregame gate;
   - combination structure is frozen before the prospective sample;
   - no retrospective search over subsets, weights, interactions, or thresholds.

## Current implications

- Dynamic Role V2 V0.2: **ineligible** — rejected.
- Game Environment V0.1: **ineligible** — rejected.
- Team TD count overdispersion V0.1: **ineligible** — rejected.
- Signed rushing pregame V0.1: **ineligible** — rejected.
- Availability/workload mixture: **not evaluable retrospectively** — prospective data collection only.
- Dynamic Role V0.1 full: **prospective-hypothesis eligible, not production eligible**; retrospective
  Fair-Line MAE improved but directional gain was not established.
- Defensive-efficiency rushing/receiving: component gates passed; eligibility depends separately on
  the still-running true-pregame ablations in PR #394.
- Market microstructure/CLV: prospective capture workflow is active; no grading until sufficient
  timestamp-qualified evidence accumulates.

## Prospective combination rule

If a PR #394 event type passes its frozen true-pregame gate, that event-type defensive-efficiency
residual becomes eligible for the future prospective shadow challenger.

The future prospective challenger may include:
- Dynamic Role V0.1 full as a separately frozen role hypothesis;
- each defensive-efficiency event type that independently passes PR #394;
- no signed-rushing overlay;
- no Game Environment V0.1 residual;
- no generic team-TD overdispersion.

The exact combination must be frozen **before** the first prospective outcome used for evaluation.
No weight fitting on 2026 outcomes is permitted.

## Production gate

No mechanism or combination can replace published Props V1 from retrospective 2023–2025 evidence.
Promotion requires a prospectively frozen sample with proper scoring, calibration, Fair-Line error,
market-relative probability diagnostics, and economic decision metrics under the separate market
policy.
