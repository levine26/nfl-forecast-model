# Phase 3 Candidate Registry

**Frozen before first development output:** yes  
**Pre-result gate:** `KEEP_FROZEN_PHASE3_CONTRACT`  
**Production model:** `F-ST-01-FROZEN-2026` — untouched

| Candidate | Class | Frozen identity | Development targets | 2025 status | 2026-selection status |
|---|---|---|---|---|---|
| A0 | football-only | `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1` | 2022, 2023, 2024 | BLOCKED until Phase 4 | BLOCKED |
| B0 | football-only | `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1` | 2022, 2023, 2024 | BLOCKED until Phase 4 | BLOCKED |
| C0 | market-aware | `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1` | 2022, 2023, 2024 | BLOCKED until Phase 4 | BLOCKED |
| D-margin | conditional | `D-CONVEX-MARGIN-V1` only if all frozen gates pass | 2022, 2023, 2024 | BLOCKED until Phase 4 | BLOCKED |
| D-total | conditional | `D-CONVEX-TOTAL-V1` only if all frozen gates pass | 2022, 2023, 2024 | BLOCKED until Phase 4 | BLOCKED |

## A0

Estimator: Ridge / penalized Gaussian team-score model.

Frozen tuning:

- alpha: `[0.1, 1, 10, 100]`;
- observation half-life in team games: `[4, 8, 16, 32]`;
- fallback: alpha `10`, half-life `16`.

Frozen numeric state:

- offense EPA/play;
- opponent defense EPA/play allowed;
- offense pass EPA/play;
- opponent defense pass EPA/play allowed;
- offense success rate;
- opponent defense success rate allowed;
- rest differential;
- home indicator.

Team offense and opponent defense indicators provide the partial-pooling team effects. Primary predictive distribution is a correlated Gaussian using covariance estimated strictly from the outer training history.

## B0

B0 is independent of A0.

Expected drives:

- Poisson regression with L2 regularization;
- alpha `[0.0, 0.1, 1.0, 10.0]`;
- fallback `1.0`;
- tune by prior-time Poisson deviance.

Drive outcomes:

- TD / FG / EMPTY;
- L2 multinomial logistic regression;
- C `[0.05, 0.2, 1.0, 5.0]`;
- fallback `0.2`;
- tune by prior-time multinomial log loss.

Final development simulation count: `10,000` per game. No alternate count family or black-box classifier is authorized.

## C0

Separate Ridge residual models for margin and total.

- alpha `[0.01, 0.1, 1, 10, 100]`;
- fallback `1.0`;
- A0 is the only football representation;
- historical market label is `historical_closing_late_benchmark_exact_horizon_opaque`.

Mandatory arms on identical rows:

- M0 market only;
- M1 market + line-level calibration only;
- M2 market + football residual information;
- M3 full C0.

## D

D is target-specific and does not exist unless every condition passes:

1. at least two constituent absolute-error series have Pearson correlation `< 0.90`;
2. nested nonnegative sum-to-one convex blend improves pooled 2022–2024 target MAE by `>= 0.10` points versus the best constituent;
3. blend beats that best constituent in both 2023 and 2024;
4. season+week block-bootstrap `P(blend MAE < best constituent MAE) >= 0.75`.

If any gate fails, disposition is exactly `ENSEMBLE_NOT_ELIGIBLE`.

## Identity-freeze rule

After the first development output exists, none of the following may change under these candidate IDs:

- estimator family;
- feature schema;
- tuning grid;
- fold chronology;
- B0 drive taxonomy/red-zone formula/rare-tail mechanism;
- C0 market horizon label;
- D gate;
- primary evaluation objective.

A material change requires a new candidate identity and cannot be justified by unfavorable Phase 3 development performance.
