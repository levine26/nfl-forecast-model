# LevLine Props 2.0 — NGS Residual Development Result

Status: **COMPLETED RETROSPECTIVE DEVELOPMENT EXPERIMENT — NOT PROMOTION EVIDENCE**

Experiment contract: `levline-props-v2-ngs-residual-development-v0.1.0`  
Workflow run: `35372847857`  
Evaluation artifact: `10559666938`  
Artifact digest: `sha256:b693ed3e537eb529aac890f2a567cac91184c3eef68efcfd38bb15b7564e822f`

## Preregistered question

Do strictly lagged Next Gen Stats player-efficiency features add incremental directional
information beyond the same sportsbook no-vig prior plus frozen LevLine V1 probability-gap
residual model?

## Result

**No stable incremental NGS signal was demonstrated.**

### Fixed-anchor stability test

Training:
- 2023 Weeks 1–9 only.

Evaluation:
- 2023 Weeks 10–18 plus qualified 2024–2025 rows.

Results:
- decided props: **4,273**
- unique games: **197**
- NGS challenger: **52.26%**
- matched market+V1 residual baseline: **52.23%**
- frozen V1: **51.03%**
- sportsbook price direction: **53.48%**
- NGS minus matched baseline: **+0.02 percentage points**
- game-clustered 95% CI for NGS minus matched baseline: **-1.11 to +1.18 pp**
- NGS accuracy game-clustered 95% CI: **50.94%–53.58%**

The primary incremental interval includes both meaningful harm and meaningful benefit. The point
estimate is effectively zero.

### Rolling-origin 2024

Training:
- 2023 only.

Evaluation:
- qualified 2024 rows.

Results:
- decided props: **3,703**
- NGS challenger: **53.17%**
- matched market+V1 residual baseline: **52.09%**
- frozen V1: **50.83%**
- sportsbook price direction: **53.52%**
- NGS minus matched baseline: **+1.08 pp**
- game-clustered 95% CI for NGS minus matched baseline: **-0.64 to +2.97 pp**
- NGS accuracy game-clustered 95% CI: **51.48%–54.81%**

The point estimate is encouraging but does not establish a stable incremental effect.

### Rolling-origin 2025 sensitivity

Training:
- 2023–2024.

Evaluation:
- qualified 2025 genuine-OPEN rows.

Results:
- decided props: **413**
- unique games: **16**
- NGS challenger: **55.21%**
- matched market+V1 residual baseline: **59.56%**
- frozen V1: **54.96%**
- sportsbook price direction: **53.75%**
- NGS minus matched baseline: **-4.36 pp**
- game-clustered 95% CI for NGS minus matched baseline: **-9.34 to +0.24 pp**

The 2025 sample is not season-wide and is too small for a standalone conclusion, but the reversal
reinforces that the 2024 improvement is not stable enough to promote.

## Coverage

- frozen forecast rows: **5,682**
- rows with at least one strictly lagged NGS state: **5,321**
- state coverage: **93.65%**
- target-week NGS rows used: **0**
- completed 2026 outcomes used for tuning: **0**

## Diagnostic subgroup observations

These are descriptive only and are not eligible for post-hoc selection:
- 2024 receptions: NGS **56.59%**, matched residual **55.87%**, market **56.11%**, V1 **52.41%**
- 2024 rushing yards: NGS **53.03%**, matched residual **52.07%**, market **52.55%**, V1 **49.04%**
- 2024 passing TDs: NGS **57.09%**, matched residual **59.39%**, market **59.00%**, V1 **49.61%**
- 2025 rushing yards: NGS **40.00%** on 75 rows

No subgroup is promoted or used to define a selective threshold.

## Scientific conclusion

The experiment **fails to establish that NGS efficiency state adds stable incremental information**
beyond the matched market+V1 residual architecture.

The NGS state implementation remains useful research infrastructure, but the current feature/model
form should **not** be placed in the frozen prospective Props 2.0 candidate based on this evidence.

This negative result is preserved so the same hypothesis cannot later be re-tested and selectively
reported without a new preregistered scientific rationale.

Production promotion remains unauthorized.
