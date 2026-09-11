# LevLine — NFL Forecast Engine / Sunday Signal

LevLine is a free, automated NFL probabilistic forecasting system with a strict point-in-time research architecture. Sunday Signal is its front-facing forecast and explanation product.

**Production status:** live on GitHub. Automated workflows maintain forecasts, immutable pregame history, market/context refreshes, validation evidence, and the Sunday Signal feed.

## Core operating rules

- **$0 automated data/API spend** unless separately authorized.
- 2026 is a live forward-test season; completed-2026 outcomes are prohibited from selecting features, model families, architecture, coefficients, hyperparameters, ensemble weights, calibration choices, or thresholds.
- Every rolling football feature is shifted before the game it predicts.
- Production and research are firewalled. Research cannot silently modify official forecasts, locks, grading, generated production outputs, or Sunday Signal.
- Source qualification is based on technical data integrity. Qualifying a source does not automatically authorize a model feature or production dependency.
- Historical predictions/locks are append-only rather than retrospectively rewritten.

## Official 2026 winner probability — F-ST-01-FROZEN-2026

LevLine's official 2026 winner probability is the frozen two-input F-ST logit stack. Its inputs are:

1. current vig-free market home-win probability; and
2. separately materialized frozen nested-PURE probability.

Registered coefficients:

- intercept: `-0.06954359363166639`
- market-logit: `1.1939087340527093`
- nested-PURE-logit: `-0.19342747983803402`

Frozen training identity is 1,615 games from 2020–2025 with canonical SHA-256 `6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0`. 2026 outcomes are excluded from fitting and model selection.

Recovered keyed OOF/final training inputs are immutable package artifacts. Production verifies identity, registered literals, reconstruction evidence and runtime provenance before scoring; reconstruction is verification-only rather than a source of mutable live coefficients. If the current market probability is unavailable, the existing legacy fallback is retained. `legacy_final_home_prob` is preserved for rollback/counterfactual grading without rewriting historical locks.

## Built forecasting foundation

- schedule-first future-game scaffold
- sequential pregame Elo
- leakage-safe rolling/EWMA offense and defense state
- pass/rush EPA splits, success rate and neutral-state context
- opponent-adjusted and QB-context research infrastructure
- walk-forward/nested model evaluation
- PURE winner-probability, margin, total and projected-score infrastructure
- model disagreement and calibration/uncertainty evaluation
- vig-free market conversion and point-in-time market research capture
- immutable prediction snapshots, T-120 locks and grading semantics
- automated weekly, standalone-game, Sunday and market-refresh workflows

## Research/data infrastructure

LevLine now has isolated research foundations for:

- point-in-time sportsbook market capture and horizon analysis
- official injury-report capture and historical availability reconstruction
- depth charts, stable player identity, roster/personnel continuity and player state
- weather, venue and travel context
- FTN process/charting and additional nflverse/NGS/PFR-derived context
- player-impact/Expected Lineup Impact explainability
- challenger models, shadow materialization, paired uncertainty and calibration validation
- source qualification, provenance, reproducibility and fail-closed research governance

Historical experiments are versioned and retain their actual disposition. Rejected candidates are not rescued through post-result tuning; dependency-blocked/source-blocked work is not mislabeled as empirical failure.

## Availability integrity work

A 2025 Weeks 1–22 composite practice-state reconstruction has been technically qualified for a narrow research scope using stable GSIS identity, official NFL historical pages and conservative pregame chronology. Final game designation remains diagnostic-only; actual current-game snaps, postgame participation and hindsight inactive status are prohibited substitutes.

The final current-roadmap historical gate is a uniform 2022–2025 source/state contract. Its audits are intentionally fail-closed: an identity or chronology hypothesis may fail without becoming a software defect. The implementation roadmap is complete when the system can collect, validate and preserve the truthful scientific disposition without weakening gates.

See `IMPLEMENTATION_STATUS.md` for the current authoritative roadmap ledger and `docs/LEVLINE_RESEARCH.md` / `research/LEVLINE_DATA_SOURCE_MATRIX.md` for research/source governance.

## Sunday Signal

Sunday Signal is the current front-facing product. The existing interface remains preserved while the implementation/validation roadmap is completed. Draft UI work is non-production unless explicitly authorized.

The post-roadmap design phase will start from the current product rather than replacing it blindly. The target is **progressive disclosure**:

- a first-time football viewer should immediately understand who LevLine favors, by how much, and why;
- an advanced user should be able to drill into probability decomposition, model-vs-market disagreement, movement, uncertainty, personnel/context, provenance and niche analytical detail.

## Repository layout

```text
config/                       model/data configuration
src/nfl_forecast/             production forecasting and support modules
research/                     isolated research, source contracts and experiments
scripts/                      production/research command-line runners
outputs/                      generated official forecast/dashboard feed
challenger_outputs/           isolated challenger/shadow artifacts
site/                         Sunday Signal front end
.github/workflows/            automated production/research validation and capture
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
python scripts/run_week.py --season 2026 --snapshot EARLY
```

The primary dashboard feed is `outputs/this_week.csv`.

## Research promotion policy

No research idea is promoted merely because it sounds football-smart or improves one point estimate. A candidate must have leakage-safe evidence under its preregistered evaluation, appropriate uncertainty/calibration checks, and explicit production authorization. The frozen F-ST model remains the official probability engine unless that process is deliberately completed.
