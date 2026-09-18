# LevLine Props Accuracy — 2023–2025 Historical Evidence

Status: **COMPLETED HISTORICAL OUT-OF-SAMPLE RECONSTRUCTION**

Frozen model reference: `research/props-integration@db5478fd735ef0cad8fd1215e8b1fb6a96a3a21d`  
Evaluation contract: `levline-props-historical-directional-v1.0`

## Headline X

**LevLine Props directional accuracy: 51.02% (2,888 wins / 5,660 decided non-push props).**

The primary population is the preregistered genuine Action Network OPEN sample:
- `book_id=30`
- inferred OPEN rows excluded
- 2023–2025 regular seasons, Weeks 1–18
- conventional two-way line markets only
- 20,000 simulations per game
- sportsbook threshold applied only after the market-agnostic football simulation

The sample contains 5,682 qualified observations, including 12 pushes and 15 model ties/no-calls, across **230 games** and **307 players**.

The preregistered coverage rule passed: at least 1,000 decided calls, at least 100 unique games, and all three seasons represented. Therefore this genuine-OPEN result remains the primary historical X; no alternate sportsbook may replace it based on observed accuracy.

## Uncertainty and baselines

- Wilson 95% interval: **49.72%–52.33%**
- Game-clustered bootstrap 95% interval: **49.47%–52.56%**
- Majority-side naive accuracy: **51.76%**
- Trailing-5 player-stat baseline: **49.98%** (N=5,580)
- LevLine Fair-Line MAE: **19.18**
- Sportsbook opening-line MAE: **15.93**

The game-clustered interval includes 50%. The current frozen model therefore does not establish directional accuracy above chance in this reconstruction. Its aggregate Fair Line is also less accurate than the historical sportsbook opening line by MAE.

## By season

| Season | W-L | Accuracy | Games |
|---|---:|---:|---:|
| 2023 | 783-768 | 50.48% | 77 |
| 2024 | 1,878-1,818 | 50.81% | 137 |
| 2025 | 227-186 | 54.96% | 16 |

The 2025 percentage is not a season-wide standalone estimate because genuine OPEN coverage contains only 16 unique games.

## By prop family

| Prop family | W-L | Accuracy |
|---|---:|---:|
| Passing yards | 239-212 | 52.99% |
| Passing TDs | 227-211 | 51.83% |
| Receptions | 962-885 | 52.08% |
| Receiving yards | 980-963 | 50.44% |
| Rushing yards | 480-501 | 48.93% |

## By position

| Position | W-L | Accuracy |
|---|---:|---:|
| QB | 674-654 | 50.75% |
| RB | 730-745 | 49.49% |
| TE | 523-478 | 52.25% |
| WR | 961-895 | 51.78% |

## Direction diagnostic

- OVER calls: 1,707-1,747 = **49.42%**
- UNDER calls: 1,181-1,025 = **53.54%**

The UNDER-call rate should not be interpreted as a validated selective edge: it equals the realized majority-side accuracy within that subgroup and was not a preregistered betting signal.

## Reproducibility

Authoritative full-season workflow run: `35363701921`

Season artifacts:
- 2023: artifact `10554984276`
- 2024: artifact `10555732152`
- 2025: artifact `10555634880`

The forecast-level CSVs were combined using the frozen aggregation rules, with a deterministic game-clustered bootstrap seed of `20260917`.

## Interpretation boundary

This is historical out-of-sample reconstruction, not prospective 2026 evidence. It does not validate profitability, MODEL EDGE ROI, or CLV. The integrated coordinator still has no retrospectively invented MODEL EDGE threshold, and no threshold or subgroup was selected after observing these outcomes.

The empirical conclusion from this test is negative: **the current frozen LevLine Props Research Beta is approximately 51% directionally accurate on the preregistered historical OPEN sample and has not demonstrated a reliable predictive edge over chance or the sportsbook opening line.**
