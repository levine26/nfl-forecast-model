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
- Groq-powered researched matchup editorial with direct-source, prose-quality, uniqueness, and full-slate gates;
- game-scoped editorial authority: a validated Groq human Read remains attached to that matchup while the deterministic LevLine paragraph is regenerated from the latest canonical forecast row;
- a validated ChatGPT safety fallback that may replace only specifically failed Groq games and may not overwrite successful Groq games;
- punctuation-only publication safety for mechanically stitched source/status text, while preserving standardized official injury/status wording;
- a fail-closed public Impact Monitor that remains explainability-only unless a probability feature is separately authorized;
- Sunday Signal desktop/mobile presentation, History receipts, Power Ratings, Model-vs-Market views, Top Signals, The Signal editorial layer, and matchup-level movement/context surfaces.

For the backend/publication release contract, see [`docs/LEVLINE_3_RELEASE.md`](docs/LEVLINE_3_RELEASE.md). For the current implementation ledger, see [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md).

## Production invariants

These are repository contracts, not optional product preferences.

- **2026 is a forward-test season.** Completed 2026 outcomes may not be used to select, tune, refit, rescue, or re-freeze production architecture/features/hyperparameters/calibration.
- **Locked forecasts stay locked.** Once an official T−120 row exists, public presentation uses that immutable row rather than a newer current/live refresh. A post-kickoff live row without an immutable pregame lock fails closed.
- **One official probability.** Supporting model/component diagnostics do not become competing public forecasts.
- **The public line is probability-implied.** Independent margin-model output stays diagnostic and must not be relabeled as the official expected margin or betting edge.
- **Research remains firewalled.** `research/`, `research_outputs/`, and `challenger_outputs/` cannot silently become production probability inputs.
- **Context stays labeled.** Research/editorial evidence is explanatory unless a feature has passed the separate validation and authorization path.
- **Editorial provider failures are game-scoped.** One failed Groq matchup must not discard successful Groq work for the rest of the slate.
- **Editorial uniqueness targets substantive prose.** Standardized official injury/status language is intentionally exempt from duplicate-prose failures; substantive matchup analysis is not.
- **Public outputs fail closed.** Contradictory winner/probability/margin/score combinations, invalid critical numeric fields, missing post-kickoff locks, or insufficient publication evidence must not be silently published.

## Sunday Signal editorial architecture

Sunday Signal intentionally separates the human matchup layer from deterministic LevLine facts.

1. **Human matchup Read:** Groq is the primary autonomous provider. A successful, validated game-specific headline and first paragraph remain authoritative for that game until superseded by a newer validated provider result.
2. **Deterministic LevLine paragraph:** current official probability, F-ST/market context, presentation line, approximate score, and final pick are regenerated from the latest canonical forecast row. Provider prose cannot freeze old model numbers.
3. **Failed-game fallback:** if Groq fails for one game, the failure is isolated. Fresh ChatGPT fallback may replace only that failed game after the same focused and full-slate validation gates. A previously validated game entry may be used only as an emergency continuity bridge and must remain flagged for fresh fallback research.
4. **Concurrent refresh safety:** pull-request validation is isolated from `main` production concurrency, and deterministic forecast-output advances may be reconciled without silently accepting changes to research-sensitive context/editorial inputs.

## Sunday Signal Check — remediated failure classes

The repository has explicit protections for the previously observed Sunday Signal Check failures:

1. **Locked forecast overwritten by a newer refresh:** `build_public_forecasts()` resolves the immutable locked row first and regression coverage verifies the locked probability/timestamp wins over a newer current row.
2. **Spreadsheet `#VALUE!` failures:** the committed forecast feed and connected dashboard were re-audited with no `#VALUE!` cells in `THIS WEEK`, `GAME DETAIL`, `RAW FEED`, or `LAST GOOD`; critical public numeric fields also fail closed during canonical forecast construction.
3. **Misleading `BIGGEST EDGE` / `Model Line` semantics:** the active product uses probability-implied line language plus explicit LevLine-vs-market probability difference. Independent margin output remains diagnostic.
4. **Standardized injury-report language treated as duplicate prose:** editorial uniqueness validators explicitly exempt recognized official availability/status scaffolding while preserving substantive seven-word uniqueness checks.
5. **Successful Groq prose erased by a later deterministic refresh:** fixed. Validated provider human prose is game-scoped and retained; only the canonical model paragraph is regenerated.
6. **One Groq failure invalidating the whole slate:** fixed. Provider/API/focused-validation failures are isolated per game and routed through the validated failed-game fallback boundary.
7. **Malformed source/status stitching such as `Achilles LevLine...`:** fixed by a punctuation-only public-text safety layer that leaves the underlying official status facts unchanged.
8. **PR validation cancelling an in-flight production Groq run:** fixed by ref-scoped workflow concurrency.

## LevLine 4 research program

LevLine 4 is active **research only**. It does not replace `F-ST-01-FROZEN-2026` or mutate historical T−120 locks.

The formal program is defined in [`research/LEVLINE_4_RESEARCH_SPEC.md`](research/LEVLINE_4_RESEARCH_SPEC.md) and the machine-readable preregistration contract [`research/levline4_prereg_v1.json`](research/levline4_prereg_v1.json).

The current research thesis is market-primary and point-in-time strict:

- preserve T−120 F-ST as the immutable accountability benchmark;
- prospectively compare genuine T−60, T−45, and T−30 information horizons rather than reconstructing them from closing lines;
- preserve official game-day inactive evidence and other player-state information with timestamp provenance;
- test player/lineup information only as incremental information conditional on the same-horizon market, to avoid double-counting news already priced by sportsbooks;
- treat de-vig, consensus, calibration, weather, score-distribution, and other enhancements as evidence-gated candidates rather than presumed improvements;
- promote nothing automatically and never use completed 2026 outcomes to rescue or retune an active candidate.

T−45 is an operational hypothesis, not a selected production lock. T−60 and T−30 remain equal-status research horizons until prospective evidence resolves the timing question.

## Research status and known guardrails

Not every research idea is a production TODO.

- Historical 2022–2025 availability qualification remains **fail-closed**. PR #148 is the terminal V3/V4 evidence receipt: the historical official postseason source could not be made complete enough without inference, so downstream availability qualification was not authorized.
- Issue #4 remains the valid future backlog item for a numerically validated conditional-scenario engine. Sunday Signal must not invent injury/weather probability deltas before those features clear chronological OOS validation.
- Issue #104 remains the canonical record of the F-ST-01 legacy original-freeze provenance exception. Later reconstruction evidence must not be relabeled as original candidate-freeze evidence, and the registered frozen identity/tolerance must not be rewritten to make the exception disappear.
- Issue #182 remains the open historical-metric provenance audit. The registered chronological OOS evidence and final-coefficient retrospective reconstruction backscore are different quantities and must remain distinctly labeled until the original metric-generation provenance is fully reconciled.
- Issue #178 is closed as completed/superseded: its purpose was to preserve the old post-100 research plan until a formal current-main LevLine 4 program existed. That formal program now lives in the research spec/contracts above.

## Repository layout

```text
src/nfl_forecast/       production forecasting, publication, context and research-support code
scripts/                CLI/build/validation/editorial entrypoints
outputs/                production-generated forecast/publication artifacts
site/                   Sunday Signal React application and browser QA
research/               preregistered research code/contracts/evidence
research_outputs/       research-only point-in-time and evaluation artifacts
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
