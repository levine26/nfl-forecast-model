# B08A — First-night game-market historical sprint (2021–2025)

**Scope frozen:** Moneyline (outright), ATS (cover / push / loss), and game total (over / push / under). **No historical TD, yardage, or player props. No injury collector.** No modifications to frozen F-ST, official history, Sunday Signal or published selections.

## Executed before Sunday

- Existing, audited 2022–2025 chronological F-ST summary is available in `evidence/FROZEN_BASELINES_2022_2025.json`; 1,087 games and per-year counts. It is a **reproduction of existing LevLine development evidence**, not a new backtest or untainted holdout.
- B08A game-level evaluator created in `betlab/historical_games.py`. It accepts only an actual joined, pre-kickoff forecast/outcome CSV, performs chronology screening, grades the independently defined ML, margin and total, reports season/market metrics, pushes, and excludes nonqualified games. No inferred historical stake or -110 bookmaker odds.
- **Not accomplished:** A newly reconstructed 2021 F-ST OOF (no equivalent archived series located); validated 2021–2025 per-game historical ML/ATS/total archive in a common comparable decision-horizon; actual-price ROI; proof that new Scout total/ATS distributions outperform market baselines.
- **2022–2025 archived historical spread odds and totals:** source horizons are opaque late/closing reference, *not* T-minus-120 or book-specific executable prices. Never backdate them.

## Source CSV schema

Required: `game_id,season,week,gameday,game_type,kickoff_utc,prediction_timestamp_utc,home_score,away_score,final_home_prob,expected_margin,expected_total,spread_line,total_line`. Optional: `market_home_prob,prediction_training_end_utc`.

**Sign convention:** `spread_line` is the *market expected HOME MARGIN*, not the bookmaker's signed home spread. JAX home -8 corresponds to `spread_line=+8`. A home cover occurs when `home_score-away_score > spread_line`. A whole-number equal margin is a push.

The evaluator **does not refit** any model. It verifies the forecast creation time precedes kickoff, not the full upstream code/feature lineage; that upstream provenance must be separately audited. Games with no verifiable pregame forecast timestamp are excluded, not filled from reconstructed closing data.

## Run commands

```bash
cd research/betting_lab
python -m unittest discover -s tests -q
python -m betlab.cli historical-games --csv /private/point_in_time_joined_games.csv --out /private/historical-audit/2021-2025-v1.json
python -m betlab.cli prop-providers --out /private/prop-provider-matrix.json
```

For tomorrow, do **not** block game-market reporting on unavailable prop feeds. The daily Scout and quote board remain research only. Separate archived historic/model summary from independently qualified live wagers; always distinguish **win accuracy** from **ATS hit rate** and **ROI at actual juice**.

## Next implementation B08B

Resolve a real game-level chronological OOF package with all relevant predictions and results, preferably from LevLine's accepted research artifacts; qualify dates and hashes; produce per-year ML proper scores, ATS hit/push rates, totals deviations; compare on same games to market-only baselines. If only opaque closing lines exist, report no true historical actionable ROI or CLV. **No new hyperparameter search based on 2021–2025 results.**