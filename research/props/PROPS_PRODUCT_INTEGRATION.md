# LevLine Props — Research Beta product integration contract

Status: product/QA lane handoff contract  
Branch: `research/props-product-qa`  
Upstream schema: `levline-props-forecast-v0.1`  
Public schema: `levline-props-public-v0.1`  
History schema: `levline-props-history-v0.1`

This layer is separate from the official LevLine winner pipeline. It consumes offensive-player prop forecasts, validates them, publishes display-safe cards, and records immutable research receipts. It does **not** alter F-ST probabilities, game picks, or winner-model artifacts.

## Required upstream artifact

Final integration must provide `outputs/props/forecasts.json`:

```json
{
  "contract_version": "levline-props-forecast-v0.1",
  "generated_utc": "2026-09-20T14:00:00+00:00",
  "forecasts": []
}
```

Every forecast requires:

- `forecast_id`: stable unique ID for the exact prospective forecast. The publisher can derive one for fixtures, but production should supply it.
- `player_identity_resolved: true` plus stable `player_id` and display `player`.
- `position`: `QB`, `RB`, `WR`, or `TE`.
- `team`, `opponent`, `game_id`.
- supported `prop_type`.
- timezone-aware `forecast_timestamp_utc`, `data_horizon_utc`, and `kickoff_utc`.
- `model.version` and `model.simulation_accounting_ok: true`.

Supported markets are exactly:

- QB: `passing_yards`, `rushing_yards`, `passing_tds`, `rushing_td`, `anytime_td`.
- RB: `rushing_yards`, `receiving_yards`, `receptions`, `rushing_td`, `receiving_td`, `anytime_td`.
- WR/TE: `receiving_yards`, `receptions`, `receiving_td`, `anytime_td`.

The publisher rejects unsupported position/market combinations.

## Model block

Yardage, receptions, and QB passing-TD O/U forecasts require:

```json
"model": {
  "version": "props-sim-v0.1",
  "mean": 86.2,
  "median": 83.5,
  "fair_line": 83.5,
  "over_probability": 0.618,
  "under_probability": 0.382,
  "push_probability": 0.0,
  "fair_odds_american": -162,
  "prediction_interval": {"low": 55.0, "high": 113.0, "coverage": 0.80},
  "simulation_count": 50000,
  "simulation_accounting_ok": true
}
```

The fair line is the producing distribution's median / approximately 50-50 threshold under the sprint charter. The product never substitutes the mean for the fair line. Integer markets must preserve explicit push mass when a push is possible. `over_probability + under_probability + push_probability` must equal 1 within numerical tolerance.

Binary TD forecasts require:

```json
"model": {
  "version": "props-sim-v0.1",
  "td_probability": 0.64,
  "expected_tds": 0.91,
  "fair_odds_american": -178,
  "simulation_count": 50000,
  "simulation_accounting_ok": true
}
```

`expected_tds` is optional. QB passing-TD O/U is a line market and therefore requires a Fair Line plus Over/Under probabilities.

## Market block

A normal line-market signal requires a valid source, pregame capture timestamp, line, both American prices, and both no-vig probabilities:

```json
"market": {
  "source": "consensus",
  "sportsbook": "consensus",
  "captured_utc": "2026-09-20T13:58:00+00:00",
  "line": 76.5,
  "over_price_american": -110,
  "under_price_american": -110,
  "no_vig_over_probability": 0.524,
  "no_vig_under_probability": 0.476
}
```

Binary TD markets use `td_price_american` and `no_vig_probability`. The market lane owns no-vig calculation; the product does not infer a two-sided no-vig baseline from a single price. Extra book-by-book, decimal-odds, consensus, dispersion, or movement fields may remain upstream and are preserved in immutable originals even if not all are displayed on the first card.

## Quality and signal inputs

Every record requires a quality object and may provide driver explanations:

```json
"data_quality": {
  "state": "HIGH",
  "critical_ok": true,
  "confidence": "HIGH",
  "notes": []
},
"signal_state": "MODEL EDGE",
"drivers": [{"label": "Route expectation", "direction": "UP"}]
```

Accepted quality states are `HIGH`, `MEDIUM`, `LOW`, and `INSUFFICIENT`. The publication floor is `MEDIUM`: `LOW` or `INSUFFICIENT` is always demoted to `NO SIGNAL`. This is a fail-closed product safety rule, not an outcome-selected betting threshold.

Accepted display states are `MODEL EDGE`, `WATCH`, and `NO SIGNAL`. The publisher **never promotes** a forecast because the edge is numerically large. It preserves a valid upstream state or demotes it to `NO SIGNAL`. Any edge/watch cutoff must be separately preregistered and cannot be selected using completed 2026 outcomes.

## Fail-closed validation

A normal signal is suppressed for unresolved identity, unsupported market, missing/invalid model output, invalid probability accounting, malformed line/price/no-vig fields, invalid Fair Line, invalid or non-timezone-aware prospective timestamps, market/model data at or after kickoff, game already started, failed simulation accounting, critical data-quality failure, quality below `MEDIUM`, or an inverted prediction interval.

The public payload retains the row as `NO SIGNAL` with machine-readable `unavailable_reasons`; it never manufactures replacement values.

## Publication

```bash
python scripts/build_props_publication.py \
  --input outputs/props/forecasts.json \
  --output outputs/props/public_props.json \
  --site-output site/public/data/props_public.json \
  --history-output site/public/data/props_history.json
```

There is intentionally no production mock fallback. CI names the checked-in fixture explicitly. If the real artifact exists but violates the contract, publication fails instead of fabricating a normal card.

## Immutable prospective history

Before kickoff, persist originals:

```bash
python scripts/update_props_history.py record --input outputs/props/forecasts.json
```

This appends `FORECAST_ORIGINAL` receipts to `outputs/props/history/forecast_originals.jsonl`. Every receipt stores the raw `original_forecast` and `original_sha256`. Identical replays are idempotent; conflicting reuse of an immutable identity fails.

Closing markets are separate `MARKET_CLOSE` events in `market_closes.jsonl` and never overwrite originals. Example input:

```json
{"closes":[{"forecast_id":"...","captured_utc":"2026-09-20T16:59:00+00:00","source":"consensus","line":78.5,"over_price_american":-110,"under_price_american":-110}]}
```

```bash
python scripts/update_props_history.py close --input close.json
```

This preserves original market line, original Fair Line, closing line, and closing price as distinct facts for closing-line-value analysis.

Results are separate `GRADE` events in `grades.jsonl`:

```json
{"results":[{"forecast_id":"...","graded_utc":"2026-09-21T02:00:00+00:00","actual_result":101.0}]}
```

```bash
python scripts/update_props_history.py grade --input results.json
```

The grader uses the **original** stored market line and emits `WIN`, `LOSS`, or `PUSH` plus the original SHA. It never edits the forecast of record.

## Product routes

- `#/props` — current research-beta board.
- `#/props/history` — original / closing market / actual / grade view.
- `#/props/about` — methodology and guardrails.

`AppCoherent` isolates Props routes so the official Sunday Signal application is not rendered or recomputed inside the Props surface. Outside the Props namespace, the existing Sunday Signal component stack remains unchanged and receives only a small Props-beta entry control.

The product is prominently labeled `LEVLINE PROPS — RESEARCH BETA` and explicitly makes no demonstrated-profitability, market-superiority, or calibration claim.

## Dashboard behavior

The existing dashboard workflow is conservative. If `outputs/props/forecasts.json` is absent, Sunday Signal builds normally and the Props surface stays unavailable. If the artifact is present, the Props publisher validates and builds it; an invalid present artifact fails rather than publishing fabricated values.

The dashboard workflow has read-only repository permissions, so the producer/integration workflow must persist prospective originals **before kickoff**. The dashboard only reads those ledgers to render history.

## Final integration checklist

1. Simulation lane emits coherent distributions and the exact model fields above.
2. Market lane supplies source/book, capture timestamp, line, two-sided prices/no-vig probabilities, and auxiliary consensus/movement data.
3. Coordinator writes the merged artifact to `outputs/props/forecasts.json` with `levline-props-forecast-v0.1`.
4. Integration runs `update_props_history.py record` before kickoff.
5. Integration runs `build_props_publication.py`; invalid critical rows become `NO SIGNAL`, malformed top-level artifacts fail.
6. Dashboard publishes `props_public.json` and `props_history.json` without changing winner-model artifacts.
7. Closing markets and results are appended later as separate events.
8. Evaluation uses immutable originals. Completed 2026 outcomes may grade the beta but may not retroactively select model architecture, weights, hyperparameters, signal thresholds, or promotion rules.
