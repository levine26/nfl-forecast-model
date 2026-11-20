# LevLine Betting Lab B08C — Existing historical game-market evidence

**Date:** October 11, 2026. **Scope:** NFL regular seasons **2022–2025**, moneyline, spread/ATS and game totals only. No player props, touchdown modeling, injury model, gambling action or production-model promotion.

## Replayed archival F-ST outright-winner predictions, 2022–2025

Game-level F-ST and market probabilities were independently re-scored from accepted frozen Phase 5 CSV outputs (2022–2024 archive, 2025 diagnostic). This exactly matches LevLine's separate historical chronological audit. These are historical, development/nonpristine forecasts, **not untouched prospective locks**.

| Season | Games | F-ST winners | Market winners | F-ST Brier | Market Brier |
|---|---:|---:|---:|---:|---:|
| 2022 | 271 | 182 | 178 | 0.211599 | **0.210327** |
| 2023 | 272 | 185 | 184 | 0.218803 | **0.218710** |
| 2024 | 272 | 195 | 195 | 0.200637 | **0.200162** |
| 2025 | 272 | 179 | 178 | **0.211578** | 0.211600 |
| **Total** | **1,087** | **741 (68.17%)** | **735 (67.62%)** | 0.210653 | **0.210199** |

Archival binary home-win labels can count tied games as `home_win=0` (no home victory); this reproduces historical model evaluation and is not moneyline settlement. Moneyline correct winner count and betting profitability are distinct. No specific bookmaker price-horizon return is established by these data.

## Replayed A0/B0/C0 archived point forecasts, 2022–2024

A separate, exact-815-game archived historical comparison used matched baseline and research-candidate OOF rows. Across **all 815 games**, each candidate's training year preceded the scored season. **These three models are not F-ST.**

| Model | Mean absolute margin error (pts) | Mean absolute total error (pts) | ML Brier (813 nontied games) |
|---|---:|---:|---:|
| **Market** | **9.418** | **10.121** | **0.209894** |
| A0 football strength | 9.883 | 10.387 | 0.227731 |
| B0 drive process | 10.213 | 11.304 | 0.233139 |
| C0 market residual | 9.439 | 10.138 | not applicable |

**ATS at original archived spread number:** A0 386 wins / 401 losses / 28 pushes = **49.05%** on resolved bets; B0 376/411/28 = **47.78%**; C0 386/401/28 = **49.05%**.

**Game totals at archived total number:** A0 419 wins / 388 losses / 8 pushes = **51.92%** on resolved selections; B0 412/395/8 = **51.05%**; C0 396/411/8 = **49.07%**.

No synthetic -110 reference rates are mislabeled sportsbook-realized ROI. Historical market reference is late/closing **with opaque exact timing**, so tradeable book price/CLV cannot be asserted.

## Additional archived 2022–2025 ATS fair-line strategy

The existing independent ATS fair-line audit contains 1,087 historical decisions: **517 wins, 541 losses, 29 pushes**, or **48.87% excluding pushes**. Classification: `NOT_ESTABLISHED`. Its reference-only -110 sensitivity ROI of -6.71% is *not* actual verified bookmaker ROI. This is a separate model family; do not combine its decisions with A0/B0/C0.

## What this means for Sunday

- Keep F-ST moneyline probabilities independent from ATS and total projected distributions.
- Base the actionable comparison on current quoted sportsbook price at the same line, game and timestamp; don't trust stale embedded lines.
- A0/B0/C0 historical results do not justify unshrunk margin/total bets; profitable market disagreement is unproven.
- Distinguish archived development, synthetic data, live forecasts, and verified bookmaker timing in all exports.
- Props are intentionally excluded from historical backtests and tracked separately via vetted external-provider projections with evidence and use permissions.

## Sources and exact reproduction

GitHub repository `levine26/nfl-forecast-model`:

- `research/spread-points-nextgen/phase5/CANDIDATE5_DEVELOPMENT_PREDICTIONS_2022_2024.csv` blob `10dc6e58c388e5d9b32fe239ef1a3118cf47c4c1`
- `research/spread-points-nextgen/phase5/CANDIDATE5_2025_DIAGNOSTIC.csv` blob `6da4af92cca0a2c0762e8f05f2d39d35ef7a201b`
- `research/spread-points-nextgen/phase3/evidence/BASELINES_2022_2024.csv` blob `ef37cf92b4023467b751fc8e56fdc2ac668f6362`
- `research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv` blob `956f9d4d4245fe6c96729e5009bef90c7f7c2332`
- `research/ats-fair-line-policy/RESULT_SUMMARY.json` blob `9d18deb14be445c982af7f8f9922486b593c8da4`

Run **separately** from `research/betting_lab` once source files are available in local checkout:

```bash
python -m betlab.cli fst-archive-audit \
  --development ../../research/spread-points-nextgen/phase5/CANDIDATE5_DEVELOPMENT_PREDICTIONS_2022_2024.csv \
  --diagnostic ../../research/spread-points-nextgen/phase5/CANDIDATE5_2025_DIAGNOSTIC.csv \
  --out /private/reports/B08C_FST_2022_2025.json
python -m betlab.cli frozen-oof-audit \
  --baselines ../../research/spread-points-nextgen/phase3/evidence/BASELINES_2022_2024.csv \
  --oof ../../research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv \
  --out /private/reports/B08C_ATS_TOTALS_2022_2024.json
```

This record contains independently reproduced numerical summaries using the GitHub connector and a Python replayer verified on controlled test inputs. A direct local full-CSV Python replay is **not claimed**, because the raw source files were not present in the isolated container. The above commands enable independent exact-source replay from a checkout. No fitting, hyperparameter changes or post-hoc rescue were undertaken.