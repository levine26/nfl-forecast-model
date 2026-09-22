# LevLine Props 2.1 — Current Handoff (2026-09-21/22)

## Canonical state

- Repository: `levine26/nfl-forecast-model`.
- Canonical current evaluation PR: **#466 — Consolidate Props 2.1 prospective evaluation on current main**.
- Frozen prospective cohort provenance is unchanged:
  - live run: `35477049179`
  - publication commit: `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
  - receipt blob: `e89cdce268fb10c5107ba6db4087107fb213555f`
  - immutable receipts: **3,439**
  - frozen games: **15**
  - frozen players: **744**
- Week 2 remains an **evaluation-only** cohort. Do not retrospectively mutate forecasts or tune a promoted model against these outcomes.

## Prospective Week 2 result already observed

The successful post-Sunday evaluation artifact from run `35662662103` graded **1,606 forecasts across 14 finalized games**. The like-for-like market-matched subset contains **359 forecasts**.

On that matched subset, the frozen Props 2.1 challenger underperformed the original sportsbook market:

- projection MAE gap (model minus original market): about **+1.375 units**
  - game-clustered 95% CI: **[+0.828, +2.001]**
- Brier-score gap: about **+0.0243**
  - game-clustered 95% CI: **[+0.0066, +0.0414]**
- log-loss gap: about **+0.1035**
  - game-clustered 95% CI: **[+0.0432, +0.1729]**
- original MODEL EDGE observations: **0**, so realized betting ROI is not measurable from this cohort.

Calibration diagnostics also indicate **systematic overconfidence**: the preregistered probability bins generally realized below their forecast probabilities. Treat that as a hypothesis-generating diagnosis, not a license to fit Week 2.

## Engineering changes already merged

- **#434** — full eligible-roster concentration semantics.
- **#446** — point-in-time depth-chart transport into live Props 2.1.
- Live depth-chart/player-state infrastructure is therefore no longer the primary scientific blocker.

## Active live-lifecycle fix

- **#459 — Treat fully started Props week as clean live no-op**
  - reason: after the final target-week game starts, a code-triggered live refresh correctly finds zero pregame games, but the workflow currently reports that expected lifecycle state as a failure.
  - intended behavior: preserve the prior valid capture and return a governed successful no-op only when there are zero pregame games **and at least one started game**.
  - any missing state for an upcoming game must still fail closed.
  - the research-firewall allowlist was updated to include the already-governed `scripts/run_levline_markets_live.py` coordinator.

## Scientific interpretation

Week 2 does **not** support a claim that Props 2.1 beats the market. The current evidence says the opposite on this cohort. The correct next step is to understand why, then preregister challengers for a future holdout.

The most important research questions are:

1. **Probability calibration / variance** — determine whether simulation distributions are too narrow, producing excessive confidence around otherwise reasonable central estimates.
2. **Market-prior architecture** — test outcome-free shrinkage/blending that treats the sportsbook line/price as a strong prior and asks whether LevLine adds residual signal rather than trying to replace the market outright.
3. **Prop-family decomposition** — analyze QB passing, QB rushing, RB rushing/receiving, receptions, WR/TE receiving, and TD markets separately. Do not average away family-specific failure modes.
4. **Opportunity vs. efficiency error attribution** — decompose projection error into volume/opportunity error versus per-opportunity efficiency error.
5. **Availability/personnel conditioning** — use the now-live point-in-time depth-chart layer to test whether starter/role certainty changes error or calibration prospectively.
6. **Dependence-aware uncertainty** — continue game-clustered inference and add player/team clustering where appropriate; do not treat thousands of correlated player props as independent observations.
7. **Market timing** — distinguish opening/earlier captured prices from later/closing information. A model may be useful as an early signal even if it cannot beat a mature close.

## Required next-stage protocol

Do **not** tune a production candidate directly on Week 2 and then report Week 2 as validation.

Instead:

1. preserve the current Week 2 evidence as immutable diagnosis;
2. preregister a small set of mechanistically justified challengers;
3. freeze their parameters before the next eligible slate;
4. capture full timestamped forecasts and sportsbook lines/prices prospectively;
5. grade only after outcomes finalize;
6. compare against the exact original market snapshots with clustered uncertainty;
7. promote nothing unless future holdout evidence shows both useful calibration and genuine incremental information beyond the market.

## Product/UI boundary

Keep Sunday Signal Props labeled research/challenger until the empirical promotion standard is met. Do not change official LevLine/F-ST winner-model probabilities, locks, grading, or governance to make Props results look better.

## What the next chat should do first

1. inspect PR #466 checks and merge only if the current-main evaluation surface remains green;
2. #459 is merged; only revisit it if post-kickoff live refresh stops no-oping cleanly;
3. use the Week 2 artifact as diagnosis only;
4. open a **new preregistered Props 2.2/next-challenger research lane** focused on calibration, market-residual signal, and opportunity-vs-efficiency attribution;
5. do not restart Props from scratch and do not reopen superseded historical PRs unless they contain a uniquely useful component not already merged or represented in #466.
