# LevLine Betting Lab — research v0.3.0

**Status: RESEARCH ONLY / UNVALIDATED / NO BETTING AUTOMATION.**

This is a standalone Python prototype. It makes **no changes** to the official Sunday Signal model, frozen F-ST artifacts, locks, production site, or betting outcomes. It does not scrape bookmakers or check injuries. No historical success rate or profitability is claimed by these tests.

## Run

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m betlab.cli ledger
python -m betlab.cli demo --samples 2000
```

Run from the project root. The `demo` uses **fabricated games, fabricated quotes, and an uncalibrated simulator**. It is intended to verify calculations, NOT select wagers.

## Modules

- `pricing.py`: American odds, implied probabilities, proportional de-vig, push-aware expected net return, normalized timestamp-qualified quotes, fractional Kelly math
- `settlement.py`: graded moneyline (including overtime ties), spread, totals, player props, TD markets, teaser/round-robin/parlay settlement and explicit push policies
- `scenarios.py`: correlated same-game betting tickets priced against an explicitly supplied joint scenario distribution; full-portfolio net return with shared scenario outcomes
- `evaluation.py`: point-in-time quote/prediction guards, push-aware grading, ROI, calibration, true later-price CLV where comparable, block-bootstrap intervals
- `player_models.py`: leak-aware prior-only player features, trainable touchdown Logistic/HGB candidates, yardage HGB baselines, season-forward holdout; no sports data included
- `joint_simulator.py`: **synthetic / uncalibrated** drive-score and TD scenario test generator; shared pace creates within-game correlations
- `risk.py`: conservative-stake *simulation* with hard $45 session budget, per-game exposure caps and no-bet gating for unqualified forecasts
- `sources.py`: create-only SHA-256 archival envelopes; qualified manual quotes; unqualified provider subquotes blocked without per-book quote timestamps
- `ledger.py`: verified append-only implementation receipts
- `live_board.py`: tomorrow-ready manual timestamp-qualified direct-operator quote board against the current LevLine CSV; no claim of validated value
- `cli.py`: manually invoked research board, synthetic demonstration and ledger audit

## What this is NOT

- No model has passed real point-in-time NFL holdout evaluation in this package.
- No odds are fetched or placed automatically. No profitable expectation is claimed.
- The synthetic scorer does not reproduce calibrated NFL key-margin frequencies.
- Historical data must be independently qualified for acquisition timestamps; nflverse *closing odds* cannot be relabeled earlier pregame snapshots.
- Player TD models are templates until point-in-time data is verified and real training/evaluation completed.
- Sportsbook parlay/teaser pricing and pushes require the **actual** operator's rules.
- The rule-based Kelly allocation is a paper simulation, not an authorization to stake money.

See `docs/HANDOFF.md`, `docs/ROADMAP.md`, `docs/SCIENTIFIC_PROTOCOL.md` and `docs/IMPLEMENTATION_LOG.jsonl` before continuing.

## Sunday pregame operating instructions

See `docs/TOMORROW_RUNBOOK.md`. Run `python -m betlab.cli board --slate ../../outputs/this_week.csv --quotes /private/direct-book.json --outdir /private/immutable-reports`. Every board row remains research-only with $0 automatic stake. Verify your direct-book quote and event time before using it.