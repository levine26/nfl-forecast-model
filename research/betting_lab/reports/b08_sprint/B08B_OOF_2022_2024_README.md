# B08B — 2022–2024 Frozen OOF Game-Market Comparison

Existing frozen source pairs: 815 matched regular-season games. **Not production F-ST and not a historical wager ROI backtest.**

Both original sources carry the listed Git blob IDs in the JSON report. Home winner ML uses two-sided proportional no-vig odds. **Two tied 2022 games are excluded from binary outright-winner scoring**, but retained in ATS and totals outcomes.

| Pooled benchmark (815 games) | Archived market | A0 candidate | B0 candidate | C0 candidate |
|---|---:|---:|---:|---:|
| Outright accuracy (813 non-ties) | 68.27% | 62.98% | 60.39% | n/a |
| ML Brier | 0.209894 | 0.227731 | 0.233139 | n/a |
| Margin MAE | 9.418405 | 9.882509 | 10.21317 | 9.438957 |
| Total MAE | 10.120859 | 10.386912 | 11.304409 | 10.137638 |
| Spread-side accuracy excluding push | n/a | 49.05% | 47.78% | 49.05% |
| Total-side accuracy excluding push | n/a | 51.92% | 51.05% | 49.07% |

The data supports using **market probabilities and market spread/total numbers as strong baselines**. Do not promote historical underperforming challengers. The current production winner model's separate 2022–2025 F-ST evaluation is not replaced or combined with these research candidates. **Actual return on executable bookmaker prices: unavailable.** The 2021 season is not a requirement, per user authorization.

Evaluator: `python -m betlab.cli frozen-oof-audit --baselines ../../research/spread-points-nextgen/phase3/evidence/BASELINES_2022_2024.csv --oof ../../research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv --out /private/B08B_OOF_RESULTS.json`. Script unit tests local: 75 passing for full Betting Lab suite; actual result computed independently from original GitHub source files, cross-check with script from repository checkout recommended.
