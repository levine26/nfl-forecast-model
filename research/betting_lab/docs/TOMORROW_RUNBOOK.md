# October 11 pregame MVP — operator runbook

**Status:** RESEARCH-ONLY manual sportsbook quote board. This package is not a validated wagering model or a live sportsbook account integration. No auto-betting, injury-report lookup, or wagers placed.

**Operational deadline:** Sunday's first scheduled game in LevLine status is `2026-10-11T13:30:00Z` (06:30 PDT). Verify exact kickoff time from an authoritative schedule: the model status alone is not an independently verified kickoff. Run BEFORE each relevant game's verified kickoff and quote expiration.

## First-time local setup

From a checkout of `levine26/nfl-forecast-model` at a version containing `research/betting_lab`:

```bash
cd research/betting_lab
python -m pip install -r requirements.txt
python -m unittest discover -s tests -q
python -m betlab.cli ledger
```

## Actual pregame research board

1. Ensure `outputs/this_week.csv` from LevLine's current `main` is a current pregame file. The lab **never edits** it.
2. On BeatTheLines (or another verified sportsbook), capture BOTH sides of each market intended for market-relative comparisons, with actual **American odds, exact side and line, book name, timestamp with timezone, event ID and verified kickoff**. Do not fabricate opposite-side quotes. A screenshot without a trustworthy observation time is insufficient for this strict workflow.
3. Copy `fixtures/manual_quote_template.json` to a private editable file; fill the direct quotes, replace the EXAMPLE source and timestamps, and set `decision_utc` to your actual analysis time. Keep the quote snapshot private if its source terms prohibit republication.
4. Run:

```bash
python -m betlab.cli board \
  --slate ../../outputs/this_week.csv \
  --quotes /path/to/direct_operator_quote_snapshot.json \
  --outdir /path/to/private/immutable-reports
```

5. The command saves a SHA-256-identifiable JSON report and readable Markdown report. Both are **create-only**; repeat capture requires a new decision time/snapshot. The report ranks sensitivity analyses but returns `NO_BET_UNVALIDATED_PROBABILITY_AND_PROSPECTIVE_EDGE` for every outcome. Do not interpret the illustrative market-margin forecast as a calibrated probability.
6. Separately record any actual entertainment-only personal wager; nothing in the program authorizes gambling or commits the $45 budget.

## Sample quote format

```json
{
  "snapshot_type": "MANUAL_DIRECT_OPERATOR_QUOTES",
  "decision_utc": "2026-10-11T04:00:00Z",
  "quotes": [
    {
      "id": "unique-book-game-selection",
      "game_id": "2026_05_PHI_JAX",
      "market": "spread",
      "selection": "JAX -8",
      "american": -110,
      "observed_utc": "2026-10-11T03:55:00Z",
      "source": "DIRECT_USER_OPERATOR_SCREEN",
      "kickoff_utc": "2026-10-11T13:30:00Z",
      "side": "home",
      "line": -8.0,
      "bookmaker": "BEATTHELINES"
    }
  ]
}
```

The example timestamps/prices are ILLUSTRATIONS and must not be presented as live or independently verified. Opposite side `PHI +8` should carry `side=away, line=+8`; for totals both sides share same numeric total. Opposing markets must have exactly equal capture timestamps to support a market-relative no-vig calculation. For moneylines, `side=home/away`, no numeric `line` is needed.

## Integrity boundaries

- The `source` must identify the real direct operator quote rather than a third-party consensus. Alexandria / StartWho per-book fields lacking original book quote timestamps are research context only.
- The market-normalized probability is not true win probability. The normal conversion from LevLine's margin/total projection is unvalidated and does not include NFL 3/7 discrete key-margin mass or precise push probabilities.
- Moneyline F-ST forecast is winner classification information, **not** demonstrated betting EV. The program does not compute robust per-leg probabilities suitable for correlated parlays/teasers.
- Do not claim complete live readiness, an accurate TD model, verified profitable bets, or validated ROI. Next steps are B08 historical/forward testing and B09 prospective capture.
- If any source's clock, bookmaker, odds, line, kickoff, or game identity cannot be verified, omit that quote; do not bypass the fail-closed gate.