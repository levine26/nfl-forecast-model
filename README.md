# LevLine + Sunday Signal

LevLine is the repository's NFL forecasting and publication engine. Sunday Signal is the consumer-facing product built on top of LevLine's canonical forecast contract.

**Production site:** https://levine26.github.io/nfl-forecast-model/

## Current production state

The current 2026 winner-probability path is `F-ST-01-FROZEN-2026`. Its public output is materialized through the canonical forecast layer rather than read directly from ad-hoc model or dashboard fields.

The production system now includes:

- the frozen F-ST official winner probability;
- a separately preserved football-only signal and vig-free market signal;
- a canonical probability-implied presentation line and coherent approximate score;
- T−120 pregame locking with immutable forecast-of-record semantics;
- append-only prediction history and postgame grading;
- hourly market refresh and scheduled pregame/model refresh workflows;
- contextual football intelligence for injuries, personnel, scheme, weather, travel, coaching, and matchup context;
- Groq-powered researched matchup editorial with direct-source, game-specific and uniqueness gates;
- game-scoped editorial authority: a validated Groq human Read remains attached to its matchup through later deterministic context refreshes, while the numerical LevLine paragraph is always regenerated from the current canonical forecast row;
- game-scoped ChatGPT editorial fallback for specifically failed Groq matchups, with the same focused and full-slate publication validators and no authority to overwrite successful Groq games;
- a fail-closed public Impact Monitor that remains explainability-only unless a probability feature is separately authorized;
- Sunday Signal desktop/mobile presentation, History receipts, Power Ratings, Model-vs-Market views, Top Signals, The Signal editorial layer, and matchup-level movement/context surfaces.

For the backend/publication release contract, see [`docs/LEVLINE_3_RELEASE.md`](docs/LEVLINE_3_RELEASE.md). For the current implementation ledger, see [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md).

## Production invariants

These are not optional product preferences; they are repository contracts.

- **2026 is a forward-test season.** Completed 2026 outcomes may not be used to select, tune, refit, rescue, or re-freeze production architecture/features/hyperparameters/calibration.
- **Locked forecasts stay locked.** Once an official T−120 row exists, public presentation uses that immutable row rather than a newer live refresh. A post-kickoff live row without an immutable pregame lock fails closed.
- **One official probability.** Supporting model/component diagnostics do not become competing public forecasts.
- **The public line is probability-implied.** Independent margin-model output stays diagnostic and must not be relabeled as the official expected margin or betting edge.
- **Research remains firewalled.** `research/`, `research_outputs/`, and `challenger_outputs/` cannot silently become production probability inputs.
- **Context stays labeled.** Research/editorial evidence is explanatory unless a feature has passed the separate validation and authorization path.
- **Editorial provider failures are game-scoped.** One bad provider response may not erase or downgrade successful researched Reads for other games.
- **Editorial uniqueness targets substantive prose.** Standardized official injury/status language is intentionally exempt from duplicate-prose failures; substantive matchup analysis is not.
- **Public outputs fail closed.** Contradictory winner/probability/margin/score combinations, invalid critical numeric fields, missing post-kickoff locks, unresolved editorial fallback, or insufficient publication evidence must not be silently published.

## Sunday Signal Check — remediated failure classes

The repository has explicit protections for the previously observed Sunday Signal Check failures:

1. **Locked forecast overwritten by a newer refresh:** `build_public_forecasts()` resolves the immutable locked row first and regression coverage verifies the locked probability/timestamp wins over a newer current row.
2. **Spreadsheet `#VALUE!` failures:** the current committed forecast feed and connected dashboard were re-audited with no `#VALUE!` cells in `THIS WEEK`, `GAME DETAIL`, `RAW FEED`, or `LAST GOOD`; critical public numeric fields also fail closed during canonical forecast construction.
3. **Misleading `BIGGEST EDGE` / `Model Line` semantics:** the active product uses probability-implied line language plus explicit LevLine-vs-market probability difference. Independent margin output remains diagnostic.
4. **Standardized injury-report language treated as duplicate prose:** the editorial uniqueness validators explicitly exempt recognized official availability/status scaffolding while preserving substantive seven-word uniqueness checks.
5. **Successful Groq Reads erased by later deterministic refreshes:** fixed. Validated Groq owns the human headline + matchup paragraph for that game; newer reporting remains visible in current evidence and may trigger a freshness advisory, while model facts are deterministically rerendered.
6. **One Groq failure taking down or replacing the whole slate:** fixed. Provider/API and focused-validation failures are isolated by `game_id`; only specifically failed games are eligible for validated ChatGPT recovery or a temporary last-good continuity bridge.
7. **Malformed injury-description stitching such as `Achilles LevLine...`:** fixed at the public text boundary with punctuation-only normalization that preserves the sourced injury/status language and all model values.
8. **PR validation cancelling an in-flight production Groq run:** fixed by scoping Groq workflow concurrency to the Git ref, isolating pull-request validation from `main` production.
9. **Daily forecast publication racing a long Groq research run:** deterministic output-only main advances can be reconciled, rerendering current LevLine model facts while context/editorial input changes still fail closed.

## LevLine 4 research status

LevLine 4 is an active **research-only** program; it is not the current production model. The preregistered specification is [`research/LEVLINE_4_RESEARCH_SPEC.md`](research/LEVLINE_4_RESEARCH_SPEC.md), with machine-readable contracts under `research/`.

Current research direction:

- preserve the production T−120 F-ST forecast of record as the accountability benchmark;
- prospectively capture genuine later information horizons, including T−60, T−45 and T−30;
- preserve point-in-time market, injury/inactive, player, weather and source provenance rather than reconstructing hindsight states;
- treat the same-horizon market as a strong prior/benchmark and require any player/model correction to demonstrate incremental evidence;
- keep all shadow forecasts and research outputs outside the production probability path unless a separately governed promotion decision is made.

The historical 2022–2025 market series is closing-market data, not a substitute for genuine matched T-minus snapshots. Later-horizon selection therefore requires prospective evidence.

## Research status and known guardrails

Not every research idea is a production TODO.

- Historical 2022–2025 availability qualification remains **fail-closed**. PR #148 is the terminal V3/V4 evidence receipt: the historical official postseason source could not be made complete enough without inference, so downstream availability qualification was not authorized. Do not treat that research lane as production-ready and do not infer healthy status from missing historical rows.
- Issue #4 remains the valid future backlog item for a numerically validated conditional-scenario engine. Sunday Signal must not invent injury/weather probability deltas before those features clear chronological OOS validation.
- Issue #104 is the canonical record of the F-ST-01 legacy original-freeze provenance exception. `F-ST-01-FROZEN-2026` is nevertheless the explicit LevLine 3 production path; older research metadata such as `production_promotion_authorized=false` is historical candidate-governance evidence and does not override the later production release decision.
- Issue #182 records the historical metric reconciliation: chronological architecture OOS metrics and the final-coefficient retrospective reconstruction backscore are different quantities and must remain separately labeled rather than treated as competing estimates of the same OOS performance.
- Issue #178 holds the future leakage-safe post-100 optimization/preregistration program. Draft PR #141 was closed after its surviving research scope was transferred there; it is not a production/UI release candidate.

## Repository layout

```text
src/nfl_forecast/       production forecasting, publication, context and research-support code
scripts/                CLI/build/validation/editorial entrypoints
outputs/                production-generated forecast/publication artifacts
site/                   Sunday Signal React application and browser QA
research/               preregistered research code/contracts/evidence
research_outputs/       off-main / research-only generated evidence when materialized locally or on research branches
challenger_outputs/     research/challenger outputs only
config/                  model/data configuration
.github/workflows/      production, research-firewall, dashboard and validation workflows
tests/                   regression, leakage, lock, publication, research and contract tests
```

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
python scripts/run_week.py --season 2026 --snapshot EARLY
```

The primary generated weekly feed remains `outputs/this_week.csv`. The public site does not treat that CSV alone as the complete consumer contract; the dashboard build materializes and validates canonical `public_forecasts.json` before deployment.

## Model identity

LevLine's registered frozen F-ST coefficients are:

- intercept: `-0.06954359363166639`
- market-logit coefficient: `1.1939087340527093`
- nested-football-logit coefficient: `-0.19342747983803402`

The registered training identity covers 1,615 games from 2020–2025 with canonical SHA-256 `6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0`. The legacy provenance exception and reconstruction limits are documented separately in issue #104 and `docs/FST_FREEZE_PROVENANCE.md`; this README does not override those guardrails.
