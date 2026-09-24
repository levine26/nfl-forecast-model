# OPEN SOURCE MODEL REVIEW

Phase 1 inspected source structure and public methodology rather than treating README performance claims as validation.

## `greerreNFL/nfelo`

Most relevant public comparator found. The active Python codebase separates model logic and utilities and includes explicit market-regression machinery. Public code/docs describe regression of model opinions toward opening/closing markets, market win-probability translation, CLV utilities and training benchmarks. A key conceptual lesson is explicit: market regression improves predictive accuracy but can mute model independence/alpha. That trade-off is directly relevant to LevLine.

The codebase also documents historical correctness fixes in margin-probability translation—important because a translation bug can manufacture apparent EV even when model line equals market. Transferable lesson: probability/EV translation deserves independent invariants and tests.

## `greerreNFL/nfelotranslation`

The 2026 package is especially relevant to M4. Source structure separates `Distribution`, `Key`, `Normalizer`, `SpreadMap`, `Translation` and validation. This is a better engineering decomposition than embedding ATS translation inside a monolithic predictor. Phase 3 should borrow the separation-of-concerns idea, not blindly copy parameters.

## `ShamgarBN/nfl-bet-engine`

The public 2026 repo has real source modules for `backtest`, `features`, `model`, `predict`, data and automation. Backtest code is explicitly split into `walkforward.py`, `ablate.py`, `metrics.py` and `tune.py`; repository description discloses a two-stage LightGBM + Monte Carlo + isotonic-calibration architecture. Transferable concepts are chronology-aware walk-forward evaluation, explicit ablation modules and calibrated probabilistic output. The repository is new/small and its public existence is not evidence that reported betting performance is independently validated.

## `dmochow/optimal_betting_theory`

Paper-linked repository with code/data/docs. This is high-value because it connects a peer-reviewed decision-theory paper to reproducible material rather than just a betting blog. Transfer: separate predicting conditional outcome distribution from deciding whether a wager has enough edge after vigorish.

## nflverse ecosystem

`nflreadr`, `nflfastR`, `nflverse-data`, `nflverse-rosters` and related packages are the strongest open public foundation for PBP, rosters, depth charts, snap counts and advanced-stat retrieval. However, convenience access is not PIT proof. Update cadence, source changes and whether historical revisions are retained must be audited per field.

Notable current limitation: nflverse documents that its injury source died after the 2024 season and currently has no 2025 injury data. Depth charts changed source after 2024; from 2025, updates carry timestamps. This makes M2's historical PIT reconstruction nontrivial and prevents assuming one continuous injury table exists through the research period.

## Other repositories/packages surveyed

The search covered `nfl-data-py`, NGBoost, GAMLSS, distributional-forest ecosystems, nfl4th and numerous public NFL Elo/prediction repositories. Most generic NFL prediction repos were shallow, legacy, poorly documented for chronology, or targeted straight-up winner accuracy rather than market-incremental ATS probability. None justified a new candidate family by itself.

## Code-audit checklist carried forward

Every external implementation used in future phases must be checked for:

- target sign and home/away spread convention;
- whether closing/future lines leak into pregame features;
- random K-fold versus chronology-clean evaluation;
- final injury/inactive/snap state used before it was known;
- side-price/vigorish handling;
- push handling at whole-number spreads;
- tail/support normalization;
- market null quality;
- reproducibility from raw public/licensed data;
- whether claimed betting returns use genuinely available historical prices.

The open-source review supports engineering patterns and candidate mechanisms; it does not import any repo's headline accuracy as LevLine evidence.