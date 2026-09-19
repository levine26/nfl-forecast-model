# LevLine + Sunday Signal

LevLine is the repository's NFL forecasting and publication engine. Sunday Signal is the consumer-facing product built on top of LevLine's canonical forecast contract.

**Production site:** https://levine26.github.io/nfl-forecast-model/

## Current production state

The current 2026 winner-probability path is `F-ST-01-FROZEN-2026`. Its public output is materialized through the canonical forecast layer rather than read directly from ad-hoc model or dashboard fields. **LevLine 4.0 is research-only and has no production authorization.**

The production system now includes:

- the frozen F-ST official winner probability;
- a separately preserved football-only signal and vig-free market signal;
- a canonical probability-implied presentation line and coherent approximate score;
- T−120 pregame locking with immutable forecast-of-record semantics;
- append-only prediction history and postgame grading;
- hourly market refresh and scheduled pregame/model refresh workflows;
- contextual football intelligence for injuries, personnel, scheme, weather, travel, coaching, and matchup context;
- Groq-powered researched matchup editorial with direct-source, focused-game, uniqueness, and full-slate gates;
- game-scoped provider authority: a validated Groq human Read remains attached to its matchup while the deterministic LevLine paragraph is regenerated from the latest canonical forecast row;
- a validated ChatGPT safety fallback that may replace only specifically failed Groq games and may not overwrite successful Groq games;
- editorial publication text-safety normalization for mechanical source-stitching defects without altering facts, standardized status language, picks, probabilities, lines, or scores;
- race-safe Groq publication reconciliation when a concurrent Daily forecast job advances deterministic output files, while contextual/editorial/code changes remain fail-closed;
- isolated PR-vs-production Groq concurrency so a pull-request validation run cannot cancel an in-flight `main` editorial production run;
- a fail-closed public Impact Monitor that remains explainability-only unless a probability feature is separately authorized;
- Sunday Signal desktop/mobile presentation, History receipts, Power Ratings, Model-vs-Market views, Top Signals, The Signal editorial layer, and matchup-level movement/context surfaces.

For the backend/publication release contract, see [`docs/LEVLINE_3_RELEASE.md`](docs/LEVLINE_3_RELEASE.md). For the current implementation ledger, see [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md). For the current research-only LevLine 4 program, see [`research/LEVLINE_4_RESEARCH_SPEC.md`](research/LEVLINE_4_RESEARCH_SPEC.md) and [`research/LEVLINE_4_EVALUATION_GOVERNANCE_V2.md`](research/LEVLINE_4_EVALUATION_GOVERNANCE_V2.md).

## Production invariants

These are not optional product preferences; they are repository contracts.

- **2026 is a forward-test season.** Completed 2026 outcomes may not be used to select, tune, refit, rescue, or re-freeze production architecture/features/hyperparameters/calibration.
- **Locked forecasts stay locked.** Once an official T−120 row exists, public presentation uses that immutable row rather than a newer live refresh. A post-kickoff live row without an immutable pregame lock fails closed.
- **One official probability.** Supporting model/component diagnostics do not become competing public forecasts.
- **The public line is probability-implied.** Independent margin-model output stays diagnostic and must not be relabeled as the official expected margin or betting edge.
- **Research remains firewalled.** `research/`, `research_outputs/`, and `challenger_outputs/` cannot silently become production probability inputs.
- **Context stays labeled.** Research/editorial evidence is explanatory unless a feature has passed the separate validation and authorization path.
- **Provider failures are game-scoped.** One Groq failure must not erase successful Groq editorial for other games; fallback remains validator-gated and editorial-only.
- **Editorial uniqueness targets substantive prose.** Standardized official injury/status language is intentionally exempt from duplicate-prose failures; substantive matchup analysis is not.
- **Public outputs fail closed.** Contradictory winner/probability/margin/score combinations, invalid critical numeric fields, missing post-kickoff locks, or insufficient publication evidence must not be silently published.

## Sunday Signal Check — remediated failure classes

The repository has explicit protections for the previously observed Sunday Signal Check failures:

1. **Locked forecast overwritten by a newer refresh:** `build_public_forecasts()` resolves the immutable locked row first and regression coverage verifies the locked probability/timestamp wins over a newer current row.
2. **Spreadsheet `#VALUE!` failures:** the current committed forecast feed and connected dashboard were re-audited with no `#VALUE!` cells in `THIS WEEK`, `GAME DETAIL`, `RAW FEED`, or `LAST GOOD`; critical public numeric fields also fail closed during canonical forecast construction.
3. **Misleading `BIGGEST EDGE` / `Model Line` semantics:** the active product uses probability-implied line language plus explicit LevLine-vs-market probability difference. Independent margin output remains diagnostic.
4. **Standardized injury-report language treated as duplicate prose:** the editorial uniqueness validators explicitly exempt recognized official availability/status scaffolding while preserving substantive seven-word uniqueness checks.
5. **Successful Groq prose erased by a later context refresh:** fixed. Validated provider headline/paragraph 1 remains authoritative per game; newer context becomes evidence/freshness advisory while current LevLine paragraph 2 is re-rendered deterministically.
6. **One Groq failure failed the whole slate:** fixed. Transport/research/validation failures are isolated to that game, and the failed game alone may use the ChatGPT/last-valid editorial safety path before full-slate validation.
7. **Malformed injury/source stitching such as `Achilles LevLine...`:** fixed by a punctuation-only public text-safety boundary that preserves source facts and standardized status wording.
8. **PR validation cancelling production Groq / Daily-output race falsely invalidating research:** fixed by ref-scoped workflow concurrency plus a tested deterministic-output reconciliation boundary.

## LevLine 4 research status

LevLine 4 is an active **research-only** program. It does not change `F-ST-01-FROZEN-2026`, the official T−120 accountability lock, or Sunday Signal production probabilities.

Current adopted research direction on `main`:

- preserve T−120 F-ST as the immutable incumbent/accountability benchmark;
- prospectively evaluate genuine T−60, T−45, and T−30 information horizons rather than reconstructing them from closing data;
- treat late multi-book market consensus as the hardest baseline;
- capture official game-day inactive evidence around T−90 with strict point-in-time provenance;
- test player/lineup information only for incremental residual value conditional on the same-horizon market;
- keep weather, score distributions, latent team-strength, and other challengers independent until their own ablation evidence justifies inclusion;
- retain **Brier score as the current preregistered primary probability metric**, with log loss, calibration, winner accuracy, temporal robustness, and same-horizon market comparison as supporting diagnostics;
- require prospective paired evidence and explicit promotion authorization before any LevLine 4 candidate can replace production.

T−45 is the leading operational hypothesis because it is after the official inactive release while leaving time for validation/publication, but it is **not selected**; T−60 and T−30 remain preregistered equal-status candidates until prospective evidence resolves the timing question.

## Research status and known guardrails

Not every research idea is a production TODO.

- Historical 2022–2025 availability qualification remains **fail-closed**. PR #148 is the terminal V3/V4 evidence receipt: the historical official postseason source could not be made complete enough without inference, so downstream availability qualification was not authorized. Do not treat that research lane as production-ready and do not infer healthy status from missing historical rows.
- Issue #4 remains the valid future backlog item for a numerically validated conditional-scenario engine. Sunday Signal must not invent injury/weather probability deltas before those features clear chronological OOS validation.
- Issue #104 remains the canonical record of the F-ST-01 legacy original-freeze provenance exception. Later reconstruction evidence must not be relabeled as original candidate-freeze evidence, and the registered frozen identity/tolerance must not be rewritten to make the exception disappear.
- Issue #178 holds the broader leakage-safe optimization/preregistration backlog. It does not itself authorize production changes.
- Issue #182 tracks the historical F-ST probability-metric reconciliation. The registered chronology-clean OOS benchmark and the final-coefficient reconstruction backscore must remain explicitly distinguished; neither may be silently rewritten to erase the provenance distinction.

## Repository layout

```text
src/nfl_forecast/       production forecasting, publication, context and research-support code
scripts/                CLI/build/validation/editorial entrypoints
outputs/                production-generated forecast/publication artifacts
site/                   Sunday Signal React application and browser QA
research/               preregistered research code/contracts/evidence
research_outputs/       prospective/research artifacts; never production probability inputs
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
