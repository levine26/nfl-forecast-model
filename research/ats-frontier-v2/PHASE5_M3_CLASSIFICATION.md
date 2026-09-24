# PHASE 5 M3 CLASSIFICATION

## Frozen identity

Candidate: `FV2-HIST-M3-DSSM-01`  
Null: `M3-NULL-MARKET-NORMAL-01`

Final Phase-5 classification: **`REJECTED`**.

## Primary hypothesis

Can a compact chronology-safe hierarchical dynamic offense/defense/QB state produce incremental football information after conditioning on the sportsbook market, where the candidate prediction is only a ridge-shrunk correction around the market center?

## OOF population

- outer development seasons: `2022–2025`, explicitly development/non-pristine;
- exact common rows: `1087`;
- completed-2026 outcomes used: `0`;
- market label: `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`.

## Primary result

- candidate CPL log loss: `0.7811502028797036`;
- market-null CPL log loss: `0.7804795705044401`;
- candidate-minus-null: `+0.0006706323752636532`;
- lower is better, so the frozen point estimate is unfavorable.

The M3-specific preregistered failure condition is triggered: `DYNAMIC_FULL` did not improve paired primary proper score versus `MARKET_ONLY`.

## Bootstrap uncertainty

Frozen 10,000-resample season-stratified NFL-week block bootstrap:

- 95% interval: `[-0.00031937461835433245, +0.0016556867645020252]`;
- descriptive `P(delta < 0)`: `0.0889`;
- weeks: `72`.

The point estimate is worse than the null and the interval leaves only a very small near-zero favorable tail while excluding a material improvement on the scale relevant to this frozen candidate/null comparison. Phase 5 does not create a new numeric SESOI after seeing results; it applies the already-frozen rejection/futility language together with M3's candidate-specific preregistered failure condition.

## Season stability

The primary delta is unfavorable in every outer season: `2022`, `2023`, `2024`, and `2025`. There is therefore no evidence that the pooled adverse direction is an artifact of a single bad season.

## Calibration-relative result

Null-side calibration was derived only from preserved canonical OOF probabilities under the exact frozen diagnostic:

- null intercept/slope: `0.0 / 0.0`;
- candidate intercept/slope: `-0.0008002656550699535 / -1.4064471514780361`.

Relative to null:

- absolute-intercept worsening: `0.0008002656550699535` < `0.03`;
- absolute slope-departure-from-1 worsening: `1.406447151478036` > `0.10`.

Thus M3 materially degrades calibration under the frozen slope rule. The protocol exception cannot apply because the primary metric did not significantly improve without post-hoc correction.

## Ablation result

Frozen preregistered ablations show:

- `DYNAMIC_NO_QB` primary log loss: `0.7808845344047226`;
- `DYNAMIC_FULL - DYNAMIC_NO_QB`: approximately `+0.0002656684749809774`;
- adding the QB state therefore worsened the primary score;
- `DYNAMIC_FULL` slightly improved on the static football-state ablation but still lost to `MARKET_ONLY`.

This is explanatory evidence only. `DYNAMIC_NO_QB` is not promoted or renamed after observing the result.

## Numerical / red-team result

- chronology/leakage audit: `PASS`;
- red-team audit: `PASS`;
- no numerical failure is the reason for rejection.

## ATS diagnostic

`518-540-29`, ex-push hit rate `48.96%`.

ATS is diagnostic only and does not enter the classification.

## Frozen clauses applied

### Eligibility clauses not satisfied

1. Candidate mean primary score better than null: **FAIL**.
2. 95% paired week-block interval entirely below 0: **FAIL**.
3. No numerical/leakage failure: **PASS**.
4. Calibration not materially degraded: **FAIL** on slope-departure rule.
5. Improvement not wholly concentrated in one season / >=10 rows: no positive improvement exists to qualify.

### Rejection clauses triggered

- Frozen M3 candidate-specific failure condition: `DYNAMIC_FULL` fails to improve the paired primary proper score versus `MARKET_ONLY`.
- Frozen Phase-5 rejection/futility condition: the candidate point estimate is worse than null, and the week-block uncertainty excludes a practically meaningful improvement while the only favorable tail is near zero.

No ATS result, QB-ablation rescue, architecture expansion, process-variance change, distribution change, or recalibration is used in this disposition.

## Scientific interpretation

The frozen M3 formulation did not establish incremental dynamic-football-state information beyond the historical market benchmark. In this version, the explicit QB state was directionally harmful on the primary score, and the full candidate's calibration slope was materially worse than its null.

## What this does not establish

This does not prove that all dynamic team-state modeling, all QB modeling, or all future player-state information is useless. It rejects this frozen historical candidate identity and its tested mechanism/version. A materially different future hypothesis would require a new identity, preregistration, governance record, and legitimate validation path.