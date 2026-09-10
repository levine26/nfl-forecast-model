# NFL Forecast Engine — Sujar+ V0.1

A free, automated NFL forecasting project inspired by Sujar Henry's public methodology and extended with leakage-safe feature engineering, walk-forward ensembles, score forecasts, uncertainty, and a separate market signal.

**Deployment status:** live on GitHub; automated forecasts publish from GitHub Actions into `outputs/`.

## Design constraints

- **$0 data/API spend**
- **No manual weekly inputs**
- nflverse / `nflreadpy` is the primary data backbone
- 2026 is treated as a live, untouched forward-test season
- Every rolling football feature is shifted before the game it predicts
- PURE and MARKET+ forecasts remain distinguishable
- Historical predictions are appended, never overwritten
- Upcoming games receive team state from the latest completed game via a schedule-first scaffold
- Each run publishes only the next unresolved NFL week/slate

## Implemented in V0.1

### Sujar baseline
- Elo
- recent win percentage via leakage-safe EWMA/rolling windows
- rest differential
- offensive EPA
- defensive EPA
- four-model ensemble: logistic, Extra Trees, XGBoost, CatBoost
- season-level expanding-window stacking

### Core Sujar+
- pass/rush EPA splits
- success rate
- neutral-game-state EPA
- rolling 3/5/8 form
- EWMA form
- offensive/defensive matchup differentials
- Elo with margin-of-victory update
- margin regression ensemble
- total regression ensemble
- projected scores
- model-disagreement metric
- vig-free market probability when moneylines exist

### Advanced data adapters
The engine already loads these on a best-effort basis without allowing a failure to block Core:
- Next Gen Stats
- FTN charting
- PFR advanced passing
- snap counts
- depth charts

Their feature integration is the next versioned research step; they are intentionally not silently mixed into V0.1 before walk-forward ablation tests.

## Repository layout

```text
config/model.yaml             model/data configuration
src/nfl_forecast/data.py      nflverse loaders
src/nfl_forecast/elo.py       sequential pregame Elo
src/nfl_forecast/features.py  leakage-safe team/matchup features
src/nfl_forecast/market.py    vig-free market conversion
src/nfl_forecast/models.py    classification/regression ensembles
src/nfl_forecast/pipeline.py  end-to-end training + prediction
scripts/run_week.py           command-line runner
outputs/                      generated CSV/JSON dashboard feed
.github/workflows/            free GitHub Actions schedules
```

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
python scripts/run_week.py --season 2026 --snapshot EARLY
```

The primary dashboard feed is `outputs/this_week.csv`.

## Free Google Sheets connection

The simplest zero-credential deployment is a **public GitHub repository**. GitHub Actions updates `outputs/this_week.csv`; Google Sheets can read that file with `IMPORTDATA` from the repository's raw URL. This requires no Google API key, no service account, and no paid data provider.

Example raw base:

```text
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/outputs
```

Then the Sheet can use:

```text
=IMPORTDATA("https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/outputs/this_week.csv")
```

## Important modeling note

Historical nflverse schedule lines are generally closing-market information. V0.1 reports them as a market benchmark, but the football model does not use closing lines in PURE historical training. Live 2026 snapshots should be timestamped when the pipeline runs.

## Next research versions

1. Opponent-adjusted EPA iterative ratings
2. Early-season Bayesian/empirical priors and roster continuity
3. NGS QB features with shrinkage
4. Pressure / OL matchup features
5. FTN motion, play action, blitz, RPO and turnover-worthy features
6. Weather through a free source such as Open-Meteo
7. Empirical prediction intervals from walk-forward residuals
8. Learned MARKET+ blending from contemporaneous 2026 snapshots rather than a fixed research blend


## Official winner-probability model — F-ST-01-FROZEN-2026

LevLine's official 2026 winner probability is the frozen two-input F-ST logit stack. Its inputs are the current vig-free market home-win probability and the separately materialized frozen nested-PURE probability. The exact registered coefficients are intercept `-0.06954359363166639`, market-logit coefficient `1.1939087340527093`, and nested-PURE-logit coefficient `-0.19342747983803402`. Frozen training identity is 1,615 games from 2020–2025 with canonical SHA-256 `6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0`; 2026 outcomes are excluded from fitting and model selection.

The recovered keyed OOF and final training inputs are committed as immutable package artifacts and verified before scoring. Ordinary production does not force a CPU-specific OpenBLAS target. If the current market probability is unavailable for a game, that game falls back to the exact legacy 75% PURE / 25% market rule. The pre-F-ST production probability is retained as `legacy_final_home_prob` for counterfactual grading and rollback; changing `ACTIVE_PRODUCTION_STRATEGY` in `fst_production.py` to `LEGACY_PRODUCTION_STRATEGY` restores the legacy path without rewriting historical locks.
