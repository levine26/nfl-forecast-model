# Q1 Preregistration — Quantile Market-Residual Model

**Candidate ID:** `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`  
**Phase-1 status:** frozen design; untrained; no candidate performance generated

## 1. Scientific question

Can compact chronology-clean football/market state improve estimation of conditional margin quantiles around the sportsbook line, beyond market-only quantile calibration?

## 2. Target and sign convention

`M = home_score - away_score`  
`L = sportsbook_home_spread` (home favorite -3 => `L=-3`)  
`R = M + L`

The model predicts quantiles of `R`.

Required synthetic grading examples before any historical run:

- home wins by 7 at `L=-3`: `R=4`, home cover;
- home wins by 3 at `L=-3`: `R=0`, push;
- home wins by 2 at `L=-3`: `R=-1`, home loss;
- home loses by 2 at `L=+3`: `R=1`, home cover.

## 3. Frozen quantiles

Exactly:

- `τ_low = 10/21 = 0.476190476190...`;
- `τ_med = 1/2`;
- `τ_high = 11/21 = 0.523809523809...`.

No additional quantile grid may be searched. These are payout-motivated reference quantiles under standard -110/no-push economics; exact wager EV is handled separately.

## 4. Learner

Primary and only Q1 V1 learner:

`sklearn.linear_model.QuantileRegressor`

with L1 penalty.

Fixed alpha grid:

`{0.001, 0.01, 0.1, 1.0}`.

For each quantile, alpha is selected only by inner rolling-origin mean pinball loss. Standardization and imputation are fit inside each training fold.

Quantile GAM, boosting, random forests, neural nets and post-result replacement learners are prohibited in V1.

## 5. Feature contract

Use exactly the compact semantic features frozen in `DATA_AND_PIT_INVENTORY.md`:

- market spread/center/favorite size;
- market total;
- no-vig moneyline probability where available;
- fixed spread-total interactions;
- pregame Elo differential;
- single shifted EWMA football-state differentials for EPA/pass/rush/success/neutral state;
- rest differential;
- required missingness indicators.

No 3/5/8-window feature explosion, player-state reconstruction, weather, news, side juice or book dispersion in V1.

## 6. Nulls/comparators

- **Q1-M0:** no residual correction (`qτ(R)=0`) as the raw quoted-line location reference.
- **Q1-M2:** identical quantile learner using **market features only**, no football state.
- **Q1:** market + compact football state.

The prior C0 mean-residual model is archived negative evidence and may be reported as context; it is not rerun as a candidate-selection competitor unless a reproducibility check requires it.

## 7. Primary Q1 metrics

For each frozen τ:

- pinball loss;
- calibration/coverage of `P(R <= qτ)≈τ`;
- market-relative quantile error by season;
- key-number/favorite-size/total fixed slices.

Secondary location metrics:

- median absolute error of `C + q0.5(R)`;
- MAE/RMSE for comparability only.

Q1 does not survive because of ATS hit rate or ROI.

## 8. Nested chronology

Outer target seasons: 2022, 2023, 2024, 2025.

For outer target season `s`, fit only data from 2015 through `s-1`.

Hyperparameter selection uses inner rolling-origin target seasons from 2019 through `s-1`; each inner target year is scored only from models fit through the prior year. If an inner fold lacks sufficient eligible rows, it is omitted with an explicit receipt rather than replaced by random K-fold.

## 9. Q1-to-Q2 handoff

Q2 may consume only chronology-clean Q1 median residual predictions. The Q2 outer target row must never receive a Q1 estimate trained or tuned on that target row/season.

## 10. Failure classification

Q1 is not considered incremental if it fails to improve preregistered pinball/probability calibration relative to the relevant market-only null. A favorable ATS slice cannot rescue failed quantile evidence.