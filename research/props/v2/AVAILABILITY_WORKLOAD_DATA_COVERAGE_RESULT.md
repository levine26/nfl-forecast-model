# LevLine Props 2.0 — Availability / Workload Historical Coverage Result

Status: **RETROSPECTIVE EVALUATION BLOCKED BY SOURCE COVERAGE — NO MODEL RESULT**  
Candidate: `P2-AVAIL-MIX`  
Contract: `levline-props-v2-availability-workload-v0.1.0`  
Production promotion authorized: **NO**

## What was attempted

The preregistered study asked whether QUESTIONABLE/DOUBTFUL availability should be modeled as a
four-state workload mixture rather than V1's binary P(active) × normal-role assumption.

The model uses only:
- historical pregame injury designations;
- stable identity;
- strictly prior snap-share role baselines;
- target-game offensive participation for football-state grading.

No prop outcomes, sportsbook results, cover results, or completed 2026 outcomes are used.

## Source-coverage finding

The first execution failed before any evaluation score because there were no source-qualified
training examples before 2023.

A source-only amendment then allowed a requested evaluation season to be excluded **before scoring**
only when it had zero prior training examples or zero target examples, while requiring at least two
source-qualified season-forward evaluation seasons.

The rerun found:

| Requested season | Prior training examples | Target examples | Status |
|---|---:|---:|---|
| 2023 | 0 | 0 | excluded — no prior training examples |
| 2024 | 0 | 0 | excluded — no prior training examples |
| 2025 | 0 | 318 | excluded — no prior training examples |

Eligible season-forward evaluation seasons: **0**.

Therefore no workload MAE, RMSE, Brier score, mixture coefficient, or development gate result is
scientifically estimable from the current historical source under the frozen chronology.

## Scientific disposition

**STOP RETROSPECTIVE AVAILABILITY-MIXTURE EVALUATION.**

Do not:
- fit on 2025 and evaluate 2025;
- use target-season participation to estimate the same target-season workload mixture;
- backfill historical statuses from final participation;
- infer injury state from snap counts;
- relax the minimum two-season requirement;
- tune state thresholds from 2026 outcomes.

The correct path is prospective data collection: preserve timestamped injury/practice/game-status
evidence plus subsequent workload outcomes, then freeze a new evaluation candidate once a sufficient
untouched training/evaluation chronology exists.

This is a data-coverage result, not evidence for or against the workload-mixture hypothesis.
