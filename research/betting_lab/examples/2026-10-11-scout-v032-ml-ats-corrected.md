# LevLine Scout — Sunday model opinions

**Slate date:** 2026-10-11 · **Games:** 13

**Status:** Model-relative watchlist, NOT qualified sportsbook prices or calibrated wagering recommendations.
The historical ATS challengers failed to establish incremental advantage versus market-only baselines. The existing winner model is market-heavy and its small advantage is statistically unresolved.
Moneyline entries show MARKET-RELATIVE shades alongside OFFICIAL F-ST winner probabilities. A shade can favor an underdog without making it the most likely winner.
Spread entries are evaluated strictly against the handicap and do NOT use F-ST moneyline win probability for ATS.
ATS and total cover chances are exploratory push-aware rounded-normal approximations. They are NOT validated NFL ATS/total distributions.
The LevLine embedded spread/total references are not timestamp-qualified executable offers. Projections may lag current injuries and odds (injuries intentionally out of scope).

**Model-implied candidates sorted by magnitude of disagreement, not by demonstrated profitability:**

## Moneyline (outright wins; not spread covers)

| Game | Official F-ST ML (home / away) | F-ST favored winner | Relative ML shade vs stored market | Model-market difference |
|---|---|---|---|---:|
| HOU @ TEN | 23.3% / 76.7% | HOU (76.7%) | HOU ML (relative to archived market, not necessarily ML favorite) | 2.29 pp |
| IND @ PIT | 54.3% / 45.7% | PIT (54.3%) | IND ML (relative to archived market, not necessarily ML favorite) | 2.03 pp |
| DET @ ARI | 28.9% / 71.1% | DET (71.1%) | DET ML (relative to archived market, not necessarily ML favorite) | 1.99 pp |
| DEN @ LAC | 34.9% / 65.1% | DEN (65.1%) | DEN ML (relative to archived market, not necessarily ML favorite) | 1.99 pp |
| LV @ NE | 61.1% / 38.9% | NE (61.1%) | LV ML (relative to archived market, not necessarily ML favorite) | 1.96 pp |
| CIN @ MIA | 23.5% / 76.5% | CIN (76.5%) | CIN ML (relative to archived market, not necessarily ML favorite) | 1.70 pp |
| BAL @ ATL | 62.2% / 37.8% | ATL (62.2%) | ATL ML (relative to archived market, not necessarily ML favorite) | 1.31 pp |
| CLE @ NYJ | 56.4% / 43.6% | NYJ (56.4%) | NYJ ML (relative to archived market, not necessarily ML favorite) | 1.28 pp |
| SF @ SEA | 58.2% / 41.8% | SEA (58.2%) | SF ML (relative to archived market, not necessarily ML favorite) | 1.09 pp |
| MIN @ NO | 46.7% / 53.3% | MIN (53.3%) | NO ML (relative to archived market, not necessarily ML favorite) | 1.01 pp |
| NYG @ WAS | 61.6% / 38.4% | WAS (61.6%) | WAS ML (relative to archived market, not necessarily ML favorite) | 0.64 pp |
| PHI @ JAX | 76.6% / 23.4% | JAX (76.6%) | PHI ML (relative to archived market, not necessarily ML favorite) | 0.50 pp |
| CHI @ GB | 47.2% / 52.8% | CHI (52.8%) | CHI ML (relative to archived market, not necessarily ML favorite) | 0.23 pp |

## Spread (cover the handicap; independent of ML)

| Game | Archived model-reference angle | Projected difference | Exploratory chance of cover / total result | Push chance | Caveats |
|---|---|---:|---:|---:|---|
| CLE @ NYJ | CLE +2.5 | 4.82 pts | 64.6% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION |
| BAL @ ATL | BAL +3 | 4.11 pts | 61.0% | 2.9% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION |
| NYG @ WAS | NYG +3.5 | 3.69 pts | 61.3% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION |
| PHI @ JAX | JAX -7.5 | 3.20 pts | 59.8% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION |
| CHI @ GB | CHI -1.5 | 2.80 pts | 58.6% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION |
| MIN @ NO | MIN -2.5 | 2.10 pts | 56.5% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION |
| LV @ NE | NE -3.5 | 1.86 pts | 55.7% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION |
| DET @ ARI | ARI +5.5 | 1.19 pts | 53.7% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION |
| HOU @ TEN | TEN +7 | 0.97 pts | 51.5% | 3.1% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION, LOW_PROJECTED_SPREAD_DISAGREEMENT |
| DEN @ LAC | LAC +3.5 | 0.89 pts | 52.8% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION, LOW_PROJECTED_SPREAD_DISAGREEMENT |
| IND @ PIT | PIT -2.5 | 0.86 pts | 52.7% | 0.0% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION, LOW_PROJECTED_SPREAD_DISAGREEMENT |
| SF @ SEA | SF +3 | 0.82 pts | 51.0% | 3.1% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION, LOW_PROJECTED_SPREAD_DISAGREEMENT |
| CIN @ MIA | MIA +7 | 0.78 pts | 50.9% | 3.1% | UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION, LOW_PROJECTED_SPREAD_DISAGREEMENT |

## Total (over/under; independent of ML)

| Game | Archived model-reference angle | Projected difference | Exploratory chance of cover / total result | Push chance | Caveats |
|---|---|---:|---:|---:|---|
| DET @ ARI | Under 54.5 | 11.57 pts | 80.2% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION, EXTREME_TOTAL_DISAGREEMENT_INDEPENDENT_VALIDATION_REQUIRED |
| PHI @ JAX | Over 41.5 | 6.78 pts | 69.0% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| HOU @ TEN | Over 37.5 | 4.49 pts | 62.9% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| MIN @ NO | Over 41.5 | 3.86 pts | 61.1% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| IND @ PIT | Over 43.5 | 3.15 pts | 59.1% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| CLE @ NYJ | Over 39.5 | 2.88 pts | 58.3% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| CHI @ GB | Under 46.5 | 2.16 pts | 56.3% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| DEN @ LAC | Over 41.5 | 1.75 pts | 55.1% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| SF @ SEA | Over 45.5 | 1.70 pts | 55.0% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| BAL @ ATL | Over 43.5 | 1.31 pts | 53.8% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| LV @ NE | Under 45.5 | 1.30 pts | 53.8% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| NYG @ WAS | Over 41.5 | 1.14 pts | 53.3% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |
| CIN @ MIA | Over 43.5 | 1.12 pts | 53.3% | 0.0% | UNVALIDATED_TOTAL_DISTRIBUTION |

## What happens next
1. Check current sportsbook prices and actual game availability. Never treat these model-reference lines as live book quotes.
2. Run `python -m betlab.cli board --slate ... --quotes ... --outdir ...` with directly observed, timestamped prices for a quote-specific sensitivity analysis.
3. Store an immutable pregame record and later grade it prospectively; do not assert actual ROI or edge until verified.

No bets were placed, no model promoted, and no automatic staking was performed.
Forecast SHA-256: `a710cb682478f5edcb31e58f6883e9014125d35af88593b4aaf987e4e921c7c6`