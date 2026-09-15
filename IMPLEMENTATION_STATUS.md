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
- LevLine 4 remains research-only and has no production authorization.

### Forecast-of-record / accountability
- T−120 pregame lock is the forecast of record.
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
- Daily forecast output advances are recognized as deterministic/reconcilable by the Groq publication lane only when the protected context/editorial/code surfaces remain unchanged.
- Pull-request Groq validation and `main` production Groq runs use ref-scoped concurrency, preventing PR activity from cancelling an in-flight production research cycle.

### Context / editorial
- Injuries and personnel context with conservative usage enrichment.
- Scheme/matchup, QB-history, coaching/staff, weather, travel, and scenario context.
- Groq researched matchup editorial with approved/direct-source validation.
- Fail-closed source, coverage, length, banned-language, focused-game and full-slate publication gates.
- Successful validated Groq headline/paragraph-1 copy remains authoritative per game across later deterministic context refreshes; current model facts are always re-rendered from the latest canonical forecast row.
- Groq API/research/prose/source failures are isolated to the affected game rather than failing or replacing successful games elsewhere in the slate.
- A failed game may use fresh ChatGPT research through the dedicated failed-game ingest path; successful Groq games are explicitly protected from fallback overwrite.
- Last already-validated editorial may be used only as a continuity bridge when Groq and fresh ChatGPT are unavailable, with `requires_chatgpt_refresh=true` recorded in status.
- Substantive editorial uniqueness checks explicitly exempt standardized official injury/status wording.
- Deterministic rationale normalization repairs clean underlength provider fragments while preserving the publication contract.
- Public text-safety normalization repairs mechanical punctuation/source-stitching defects such as body-part text running directly into an editorial guardrail, without modifying facts or LevLine numbers.

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
| Later context refresh erased successful Groq human Reads | **Fixed and regression-tested.** Provider authority is game-scoped; deterministic paragraph 2 is regenerated from current canonical numbers. |
| One Groq failure contaminated or failed the full slate | **Fixed and regression-tested.** Provider/API/focused-validation failure is isolated per game and validator-gated fallback applies only to that game. |
| ChatGPT fallback could overwrite successful Groq work | **Fixed and regression-tested.** Partial fallback manifests are restricted to games explicitly marked `requires_chatgpt_refresh`. |
| Malformed source/injury stitching such as `Achilles LevLine...` | **Fixed and regression-tested.** Publication text safety is punctuation-only and preserves source/status/model semantics. |
| PR Groq CI cancelled an in-flight production Groq run | **Fixed and regression-tested.** Concurrency is scoped by `github.ref`. |
| Concurrent Daily output publish caused false stale-research failure | **Fixed and regression-tested.** Deterministic output changes can be reconciled while context/editorial/code changes remain fail-closed. |
| Stale implementation roadmap/docs | **Remediated again.** README and this ledger now describe the current editorial fallback, race-safety and LevLine 4 research boundaries. |

## Research-only / unresolved by design

### LevLine 4 prospective research program
The adopted `main` contract lives in `research/LEVLINE_4_RESEARCH_SPEC.md` and `research/LEVLINE_4_EVALUATION_GOVERNANCE_V2.md`.

Current production-safe research posture:
- T−120 F-ST remains the immutable accountability incumbent.
- Genuine T−60, T−45 and T−30 horizons are prospective candidates; no historical closing-line reconstruction may masquerade as matched T-minus evidence.
- Official game-day inactive evidence around T−90 is valuable only with timestamped point-in-time provenance.
- Late same-horizon market consensus is the baseline to beat; player/lineup features must prove residual value conditional on that market state.
- The currently adopted preregistered primary probability metric remains **Brier score**; log loss, calibration, winner accuracy, same-horizon market comparison and temporal robustness are supporting diagnostics.
- T−45 is an operational hypothesis, not a selected horizon.
- No candidate can enter production without prospective paired evidence plus explicit promotion authorization.

### Historical availability qualification
The 2022–2025 availability lane remains fail-closed. PR #148 records the terminal V3/V4 result: available historical sources could not establish a complete deterministic official-club final injury-report dataset for all affected postseason team-weeks without inference. Downstream qualification was therefore not executed. No production feature should be promoted from this failed lane unless a new independently verifiable source resolves the missing coverage before downstream metrics are inspected.

### Conditional scenario engine — issue #4
The presentation/guardrails exist, but alternative numerical scenario probabilities remain future research. They may be produced only from features that independently pass chronological OOS validation and remain explicitly conditional/separate from the official forecast.

### F-ST legacy freeze provenance — issue #104
The current guardrails/reconstruction evidence are implemented, but the missing original pre-fit candidate-freeze provenance cannot be recreated retroactively. Later evidence must remain labeled as reconstruction/shadow evidence; registered identity/tolerance cannot be rewritten to erase the exception.

### Post-100 research program — issue #178
The surviving leakage-safe optimization/preregistration program from draft PR #141 now lives in issue #178 as research backlog. Any actual challenger implementation should be split into a fresh, narrowly scoped research PR against current `main`, and completed 2026 outcomes remain prohibited for selection/tuning.

### F-ST historical probability metric reconciliation — issue #182
The chronology-clean OOS architecture benchmark and the backscore obtained by applying final target-2026 coefficients across prior seasons are distinct quantities. Issue #182 remains the audit record until the exact historical-evidence lineage is fully reconciled. Production coefficients/identity and the original evidence must not be rewritten to make the discrepancy disappear.

## Repository hygiene disposition

- PR #128: closed as superseded by the shipped Sunday Signal redesign/product layer.
- PR #151: closed as superseded by the Groq production editorial pipeline already on `main`.
- PR #163: closed as superseded by the broader underlength-rationale repair already on `main`.
- PR #141: closed after its surviving post-100 research scope was transferred to issue #178; its product-vision material was already superseded by shipped PRs #174/#175.
- PR #176: merged after full responsive, dashboard, research-firewall, and F-ST validation; fixes Week Board typography and adds Sunday Signal Check browser guards.
- PR #177: merged; repository status/docs were reconciled to the active production architecture.
- PR #195: merged after all required gates; implements per-game provider authority, failed-game ChatGPT fallback, text-safety normalization, and updated Sunday Signal Check behavior.
- PR #197: merged after full model-regeneration, Groq, and firewall validation; isolates PR/production Groq concurrency and hardens reconciliation against concurrent deterministic Daily output publishes.
- Issues #4, #104, #178, and #182 intentionally remain open because they are real research/governance records, not stale production defects.
- Active in-use PRs are intentionally not summarized here until they merge or close; this ledger describes adopted `main` behavior only.

## Non-negotiable research firewall

- Completed 2026 outcomes may not select, tune, refit, rescue, or re-freeze production architecture/features/hyperparameters/calibration.
- Research-only sources/features may not silently become production probability inputs.
- Historical locked forecasts may not be mutated.
- Missing/insufficient point-in-time evidence must fail closed rather than be inferred.
- Unmerged research policy proposals do not supersede the preregistered contracts already adopted on `main`.
