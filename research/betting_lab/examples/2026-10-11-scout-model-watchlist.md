# LevLine Scout — Sunday model opinions

**Slate date:** 2026-10-11 · **Games:** 13

**Status:** Model-relative watchlist, NOT qualified sportsbook prices or calibrated wagering recommendations.
The historical ATS challengers failed to establish incremental advantage versus market-only baselines. The existing winner model is market-heavy and its small advantage is statistically unresolved.
Moneyline entries are model-minus-market *relative shades*, not the official most-likely winner or a bet to place.
The LevLine embedded spread/total references are not timestamp-qualified executable offers. Projections may lag current injuries and odds (injuries intentionally out of scope).

**Model-implied candidates sorted by magnitude of disagreement, not by demonstrated profitability:**

## Spread

| Model opinion | Disagreement | Audit flags |
|---|---:|---|
| CLE +2.5 (CLE @ NYJ) | 4.82 pts | WINNER_MARGIN_DISAGREEMENT |
| BAL +3 (BAL @ ATL) | 4.11 pts | WINNER_MARGIN_DISAGREEMENT |
| NYG +3.5 (NYG @ WAS) | 3.69 pts | WINNER_MARGIN_DISAGREEMENT |
| JAX -7.5 (PHI @ JAX) | 3.20 pts | None |
| CHI -1.5 (CHI @ GB) | 2.80 pts | None |
| MIN -2.5 (MIN @ NO) | 2.10 pts | None |
| NE -3.5 (LV @ NE) | 1.86 pts | None |
| ARI +5.5 (DET @ ARI) | 1.19 pts | None |
| TEN +7 (HOU @ TEN) | 0.97 pts | LOW_PROJECTED_SPREAD_DISAGREEMENT |
| LAC +3.5 (DEN @ LAC) | 0.89 pts | LOW_PROJECTED_SPREAD_DISAGREEMENT |
| PIT -2.5 (IND @ PIT) | 0.86 pts | LOW_PROJECTED_SPREAD_DISAGREEMENT |
| SF +3 (SF @ SEA) | 0.82 pts | LOW_PROJECTED_SPREAD_DISAGREEMENT |
| MIA +7 (CIN @ MIA) | 0.78 pts | LOW_PROJECTED_SPREAD_DISAGREEMENT |

## Moneyline

| Model opinion | Disagreement | Audit flags |
|---|---:|---|
| HOU ML (relative model-market shade only) (HOU @ TEN) | 2.29 pp | None |
| IND ML (relative model-market shade only) (IND @ PIT) | 2.03 pp | MODEL_RELATIVE_LEAN_OPPOSES_FST_WINNER_PICK |
| DET ML (relative model-market shade only) (DET @ ARI) | 1.99 pp | TINY_PROBABILITY_DIFFERENCE |
| DEN ML (relative model-market shade only) (DEN @ LAC) | 1.99 pp | TINY_PROBABILITY_DIFFERENCE |
| LV ML (relative model-market shade only) (LV @ NE) | 1.96 pp | MODEL_RELATIVE_LEAN_OPPOSES_FST_WINNER_PICK, TINY_PROBABILITY_DIFFERENCE |
| CIN ML (relative model-market shade only) (CIN @ MIA) | 1.70 pp | TINY_PROBABILITY_DIFFERENCE |
| ATL ML (relative model-market shade only) (BAL @ ATL) | 1.31 pp | WINNER_MARGIN_DISAGREEMENT, TINY_PROBABILITY_DIFFERENCE |
| NYJ ML (relative model-market shade only) (CLE @ NYJ) | 1.28 pp | WINNER_MARGIN_DISAGREEMENT, TINY_PROBABILITY_DIFFERENCE |
| SF ML (relative model-market shade only) (SF @ SEA) | 1.09 pp | MODEL_RELATIVE_LEAN_OPPOSES_FST_WINNER_PICK, TINY_PROBABILITY_DIFFERENCE |
| NO ML (relative model-market shade only) (MIN @ NO) | 1.01 pp | MODEL_RELATIVE_LEAN_OPPOSES_FST_WINNER_PICK, TINY_PROBABILITY_DIFFERENCE |
| WAS ML (relative model-market shade only) (NYG @ WAS) | 0.64 pp | WINNER_MARGIN_DISAGREEMENT, TINY_PROBABILITY_DIFFERENCE |
| PHI ML (relative model-market shade only) (PHI @ JAX) | 0.50 pp | MODEL_RELATIVE_LEAN_OPPOSES_FST_WINNER_PICK, TINY_PROBABILITY_DIFFERENCE |
| CHI ML (relative model-market shade only) (CHI @ GB) | 0.23 pp | TINY_PROBABILITY_DIFFERENCE |

## Total

| Model opinion | Disagreement | Audit flags |
|---|---:|---|
| Under 54.5 (DET @ ARI) | 11.57 pts | EXTREME_TOTAL_DISAGREEMENT_INDEPENDENT_VALIDATION_REQUIRED |
| Over 41.5 (PHI @ JAX) | 6.78 pts | None |
| Over 37.5 (HOU @ TEN) | 4.49 pts | None |
| Over 41.5 (MIN @ NO) | 3.86 pts | None |
| Over 43.5 (IND @ PIT) | 3.15 pts | None |
| Over 39.5 (CLE @ NYJ) | 2.88 pts | None |
| Under 46.5 (CHI @ GB) | 2.16 pts | None |
| Over 41.5 (DEN @ LAC) | 1.75 pts | None |
| Over 45.5 (SF @ SEA) | 1.70 pts | None |
| Over 43.5 (BAL @ ATL) | 1.31 pts | None |
| Under 45.5 (LV @ NE) | 1.30 pts | None |
| Over 41.5 (NYG @ WAS) | 1.14 pts | None |
| Over 43.5 (CIN @ MIA) | 1.12 pts | None |

## What happens next
1. Check current sportsbook prices and actual game availability. Never treat these model-reference lines as live book quotes.
2. Run `python -m betlab.cli board --slate ... --quotes ... --outdir ...` with directly observed, timestamped prices for a quote-specific sensitivity analysis.
3. Store an immutable pregame record and later grade it prospectively; do not assert actual ROI or edge until verified.

No bets were placed, no model promoted, and no automatic staking was performed.
Forecast SHA-256: `a710cb682478f5edcb31e58f6883e9014125d35af88593b4aaf987e4e921c7c6`