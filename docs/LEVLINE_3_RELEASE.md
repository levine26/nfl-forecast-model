# LevLine 3.0 — Production Release Contract

LevLine 3.0 is the production release of the canonical coherent forecast and publication layer used by Sunday Signal. This launch lane is deliberately non-visual: it does not redesign, restyle, rebrand, or otherwise change the Sunday Signal UI. UI/UX work is isolated to a separate effort.

## Production invariants

- The official 2026 winner-probability model remains `F-ST-01-FROZEN-2026`.
- This release does not refit, retune, replace, or promote a new forecasting architecture.
- The canonical public forecast remains the single source of truth for the displayed winner, win probability, probability-implied line, approximate score, market comparison, timestamps, and lifecycle state.
- The first valid T−120 pregame lock remains immutable and is the forecast of record.
- Post-kickoff live rows may not replace a missing immutable pregame lock.
- Contradictory public winner/probability/margin/score combinations fail closed.
- Independent margin-model output remains diagnostic and is not relabeled as the official public expected margin.
- Research-only player/impact signals remain explainability-only unless separately authorized for probability production.

## Publication/runtime scope

Sunday Signal remains the existing publication surface. LevLine 3.0 changes only the forecast/publication contract and editorial research runtime behind that surface:

- weekly canonical forecast semantics remain coherent and fail closed;
- deterministic numerical explanation uses the frozen F-ST signal, vig-free market signal, official probability, probability-implied presentation line, and coherent score;
- stale fixed 75% PURE / 25% market wording is removed from the publication path;
- qualitative media research moves from GitHub Copilot runtime to Groq Compound with approved-domain web research and strict source validation; and
- existing immutable 2026 history, grading, locks, methodology, and data-contract behavior are preserved.

No `site/` source, style, component, asset, or responsive-test file is part of this release diff.

## Version semantics

`LevLine 3.0` is the backend/publication release version. The canonical public forecast payload's `contract_version` is a separate schema version and is intentionally not changed by this launch.

## Release gate

The launch is eligible to merge only after the existing model, research-firewall, dashboard-build, responsive, contextual-intelligence, editorial-provider, and production-deployment workflows pass against the launch branch. After merge, the existing site must still deploy successfully without any visual-source changes, and a real Groq-powered full-slate editorial refresh on `main` must clear the publication gates before LevLine 3.0 is considered fully launched.
