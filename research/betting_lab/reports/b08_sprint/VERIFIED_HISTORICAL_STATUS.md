# LevLine game-market historical readiness — 2026-10-10 night

**Existing evidence, not a freshly computed historical backtest.** Verified against existing `research/levline3_chronological_accuracy_audit_v1.json`, GitHub blob `e0334e1ca175561e9e551ebf88a19eea2933a3c6`.

| Regular season | F-ST wins | Games | Accuracy | Market wins | Market accuracy |
|---|---:|---:|---:|---:|---:|
| 2021 | unavailable | — | — | — | — |
| 2022 | 182 | 271 | 67.16% | 178 | 65.68% |
| 2023 | 185 | 272 | 68.01% | 184 | 67.65% |
| 2024 | 195 | 272 | 71.69% | 195 | 71.69% |
| 2025 | 179 | 272 | 65.81% | 178 | 65.44% |
| **2022–25** | **741** | **1,087** | **68.17%** | **735** | **67.62%** |

Across 2022–25, the chronology-clean F-ST has a **worse Brier score** (0.210653 vs market 0.210199) and worse log loss (0.608713 vs 0.607647) notwithstanding six additional binary winners. The difference in the paired accuracy evidence was not statistically conclusive.

**ATS:** The prior LevLine ATS NextGen Q1 and Q3 incremental models were rejected on frozen proper scores; Q2 failed its prespecified support contract. Q3's nonpush development hit rate was 52.17% compared with the market-only 52.84%. These do **not** describe fresh Betting Lab v0.3.2 cover-probability validation. Closing spread benchmarks are not verified playable odds at a known earlier decision horizon.

**Totals:** No similarly qualified 2021–25 independent OOS total-probability record has been established in this run. Do not label a difference between forecast mean and historic market total as a validated probability edge.

**Reality check:** This implementation added historical audit *machinery* that can grade supplied pregame forecast rows, but did not obtain the full signed/provenanced row-level combined dataset for all seasons tonight. Therefore no new per-game backtest claims or actionable ROI estimate are made. Historical moneyline evidence is 2022–25 only. The 2021 gap cannot be filled via retrospective predictions from the current 2026-frozen model.