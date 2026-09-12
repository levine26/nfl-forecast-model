# Implementation Status

_Last reconciled: 2026-09-12_

This file is the authoritative high-level implementation ledger. Historical research documents remain useful evidence, but they should not be read as the current production roadmap.

## Production — built and active

### Forecast/model contract
- Frozen official 2026 winner-probability path: `F-ST-01-FROZEN-2026`.
- Separately preserved football-only and market signals.
- Canonical public forecast contract with one official winner/probability.
- Probability-implied presentation margin/line derived from the official probability.
- Independent margin model preserved only as a diagnostic.
- Coherent projected-score presentation tied to the official probability direction.
- Fail-closed contradiction checks for winner/probability/margin/score semantics.

### Forecast-of-record / accountability
- T−120 pregame lock is the production forecast of record.
- Immutable lock rows take precedence over later current/live rows in public presentation.
- Post-kickoff publication without a valid immutable pregame lock is rejected.
- Prediction history is append-only and graded without rewriting the original receipt.
- 2026 History is a first-class Sunday Signal surface.

### Data / scheduled production
- nflverse schedule/results/PBP/EPA pipeline.
- Sequential pregame Elo and leakage-safe rolling/EWMA team features.
- Market implied-probability conversion and recurring market refresh.
- Pregame/daily production workflows with generated-output reconciliation.
- Power-rating and diagnostic publication feeds.

### Context / editorial
- Injuries and personnel context with conservative usage enrichment.
- Scheme/matchup, QB-history, coaching/staff, weather, travel, and scenario context.
- Groq researched matchup editorial with approved/direct-source validation.
- Fail-closed source, coverage, length, banned-language and full-slate publication gates.
- Substantive editorial uniqueness checks with explicit exemption for standardized official injury/status wording.
- Deterministic rationale normalization for clean underlength provider fragments while preserving final publication contracts.
- Validated Groq human prose is authoritative per game; later deterministic context refreshes do not erase successful provider work.
- Deterministic LevLine paragraph 2 is always regenerated from the current canonical forecast row, so retained provider prose cannot freeze stale model values.
- Groq API/transport/focused-validation failures are isolated to the affected game.
- ChatGPT failed-game fallback may replace only explicitly failed games, must pass focused and full-slate validators, and cannot overwrite successful Groq games.
- Last-valid editorial may be used only as a temporary continuity bridge and remains flagged for fresh ChatGPT replacement.
- Public text safety repairs punctuation-only mechanical stitching such as `Achilles LevLine...` without changing official status facts or model values.
- Groq workflow concurrency is scoped by ref so pull-request validation cannot cancel an in-flight `main` production run.
- Concurrent deterministic forecast-output advances can be reconciled while research-sensitive context/editorial inputs remain fail-closed.

### Sunday Signal product
- Premium responsive desktop/mobile UI.
- Top Signals, search, Model vs Market, Signal Strength presentation tiers, What Changed, The Signal, research provenance, Forecast Movement, Key Developments, Power Ratings, History receipts, and methodology/technical disclosure.
- Presentation tiers are derived UI shorthand only; they are not new model outputs.
- Fail-closed Impact Monitor remains explainability-only unless a probability feature is separately authorized.
- Responsive/browser QA covers 1440, 1180, 1024, 768, 430, 390, and 320 widths.
- Week Board row typography is explicitly pinned to the normal-width UI stack, with browser regression coverage preventing reintroduction of condensed/compressed matchup text.

## Sunday Signal Check remediation status

| Check finding | Current disposition |
| --- | --- |
| Locked forecast replaced by a newer live refresh | **Fixed and regression-tested.** Canonical public build selects the immutable lock row first. |
| Current-week `#VALUE!` spreadsheet errors | **Currently clean.** Repository feed and connected dashboard tabs `THIS WEEK`, `GAME DETAIL`, `RAW FEED`, and `LAST GOOD` were re-audited with no `#VALUE!` matches. Active browser QA also rejects `#VALUE!` on the Week Board. |
| Ambiguous `BIGGEST EDGE` / `Model Line` semantics | **Retired and regression-tested.** Public presentation distinguishes probability-implied line, market line, and LevLine-vs-market probability difference; active browser QA rejects the stale labels. |
| Standardized injury-report wording triggering uniqueness failures | **Fixed and regression-tested.** Recognized factual/status scaffolding is exempt; substantive prose is still checked. |
| Compressed/condensed Week Board typography | **Fixed and regression-tested.** Matchup-row text uses the normal UI font stack with normal stretch/variant/kerning. |
| Successful Groq Read erased by later deterministic reporting | **Fixed.** Human provider authority is game-scoped; newer reporting is advisory/current evidence, while paragraph 2 is regenerated from canonical model state. |
| Single Groq failure failing/replacing the entire slate | **Fixed.** Provider failures are isolated per game and route through the failed-game fallback boundary. |
| ChatGPT fallback overwriting successful Groq games | **Blocked by contract.** Partial fallback manifests may name only games explicitly marked as failed/requiring refresh. |
| Malformed injury/body-part stitching in public prose | **Fixed.** Punctuation-only public text safety runs before final editorial QA. |
| PR Groq validation cancelling production Groq | **Fixed.** Workflow concurrency is ref-scoped. |
| Deterministic Daily output advance falsely treated as stale provider research | **Fixed.** Reconciliation distinguishes deterministic output advances from research-sensitive context/editorial changes. |
| Stale implementation roadmap/docs | **Remediated.** README and this ledger describe the active production system and formal LevLine 4 research program. |

## LevLine 4 — active research-only program

The former post-100 backlog has been replaced by a formal preregistered current-main program. The canonical human-readable spec is `research/LEVLINE_4_RESEARCH_SPEC.md`; the machine-readable preregistration is `research/levline4_prereg_v1.json`.

### Two-clock architecture
- **Clock A — production/accountability:** immutable T−120 `F-ST-01-FROZEN-2026` forecast of record.
- **Clock B — research shadows:** T−60, T−45, and T−30 final-probability candidates.
- Research shadows cannot rewrite Clock A history.
- T−45 is an operational hypothesis only, not a selected production horizon.

### Current research thesis
- Strong same-horizon multi-book market consensus is the primary benchmark/prior.
- Player/lineup information is tested only for incremental residual value conditional on that market state.
- Official game-day inactive evidence and other late information must be captured prospectively with timestamp provenance.
- Historical closing lines may not be relabeled as matched T−60/T−45/T−30 snapshots.
- De-vig, consensus, calibration, weather, score-distribution, and other candidate layers remain evidence-gated rather than assumed improvements.
- Completed 2026 outcomes may grade frozen candidates but may not rescue, retune, or repeatedly refit an active evaluation.

## Research-only / unresolved by design

### Historical availability qualification
The 2022–2025 availability lane remains fail-closed. PR #148 records the terminal V3/V4 result: available historical sources could not establish a complete deterministic official-club final injury-report dataset for all affected postseason team-weeks without inference. Downstream qualification was therefore not executed. No production feature should be promoted from this failed lane unless a new independently verifiable source resolves the missing coverage before downstream metrics are inspected.

### Conditional scenario engine — issue #4
The presentation/guardrails exist, but alternative numerical scenario probabilities remain future research. They may be produced only from features that independently pass chronological OOS validation and remain explicitly conditional/separate from the official forecast.

### F-ST legacy freeze provenance — issue #104
The current guardrails/reconstruction evidence are implemented, but the missing original pre-fit candidate-freeze provenance cannot be recreated retroactively. Later evidence must remain labeled as reconstruction/shadow evidence; registered identity/tolerance cannot be rewritten to erase the exception.

### Historical F-ST metric reconciliation — issue #182
The registered chronological 2022–2025 architecture OOS metrics and the retrospective backscore obtained by applying the final 2026 frozen coefficients to those historical rows are distinct quantities. They must remain separately labeled. The original metric-generation provenance is still being reconciled and no frozen coefficient or production behavior should be changed to make the numbers match.

### Superseded post-100 backlog — issue #178
Issue #178 is closed as completed/superseded. Its purpose was to preserve the old PR #141 research plan until a formal current-main LevLine 4 program existed. That program now lives in the research specification/contracts above.

## Repository hygiene disposition

- PR #128: closed as superseded by the shipped Sunday Signal redesign/product layer.
- PR #151: closed as superseded by the Groq production editorial pipeline already on `main`.
- PR #163: closed as superseded by the broader underlength-rationale repair already on `main`.
- PR #141: closed after its surviving post-100 research scope was transferred to issue #178; its product-vision material was already superseded by shipped PRs #174/#175.
- PR #176: merged after full responsive, dashboard, research-firewall, and F-ST validation; fixes Week Board typography and adds Sunday Signal Check browser guards.
- PR #177: merged; repository status/docs were reconciled to the active production architecture.
- PR #195: merged after full CI; fixed game-scoped provider authority, ChatGPT failed-game fallback, and public editorial text safety.
- PR #197: merged after full CI; isolated Groq workflow concurrency by ref and hardened deterministic-output reconciliation during concurrent Daily publishes.
- Issue #178: closed as superseded by the formal LevLine 4 preregistered program.
- Issues #4, #104, and #182: intentionally remain open because they are real research/governance records, not stale production defects.

Active unmerged PRs are intentionally not listed here as shipped capability.

## Non-negotiable research firewall

- Completed 2026 outcomes may not select, tune, refit, rescue, or re-freeze production architecture/features/hyperparameters/calibration.
- Research-only sources/features may not silently become production probability inputs.
- Historical locked forecasts may not be mutated.
- Missing/insufficient point-in-time evidence must fail closed rather than be inferred.
