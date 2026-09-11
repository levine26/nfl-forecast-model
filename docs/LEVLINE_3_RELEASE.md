# LevLine 3.0 — Production Release Contract

LevLine 3.0 is the public-product release of the canonical coherent forecast layer used by Sunday Signal.

## Production invariants

- The official 2026 winner-probability model remains `F-ST-01-FROZEN-2026`.
- This release does not refit, retune, replace, or promote a new forecasting architecture.
- The canonical public forecast remains the single source of truth for the displayed winner, win probability, probability-implied line, approximate score, market comparison, timestamps, and lifecycle state.
- The first valid T−120 pregame lock remains immutable and is the forecast of record.
- Post-kickoff live rows may not replace a missing immutable pregame lock.
- Contradictory public winner/probability/margin/score combinations fail closed.
- Independent margin-model output remains diagnostic and is not relabeled as the official public expected margin.
- Research-only player/impact signals remain explainability-only unless separately authorized for probability production.

## Public product

Sunday Signal is the publication surface, powered by LevLine 3.0. The active site exposes:

- weekly canonical forecasts;
- per-game signal decomposition and market comparison;
- forecast movement and timestamp provenance;
- methodology and technical provenance;
- team and power-rating context; and
- immutable 2026 forecast history and grading.

## Version semantics

`LevLine 3.0` is the product/release version. The canonical public forecast payload's `contract_version` is a separate schema version and is intentionally not changed by this launch.

## Release gate

The launch is eligible to merge only after the existing GitHub Pages build and responsive Playwright workflow pass against the launch branch. Those workflows rebuild the canonical public forecast artifact from production outputs before testing the site.
