# LevLine — Alexandria Point-in-Time Data Feasibility (Research Only)

**Date:** 2026-10-07  
**Status:** FEASIBILITY / NOT AN APPROVED PREDICTIVE FEATURE SET  
**Governing roadmap:** [LEVLINE_POST_WEEK4_MODEL_IMPROVEMENT_PLAN.md](LEVLINE_POST_WEEK4_MODEL_IMPROVEMENT_PLAN.md)  
**Prior findings:** [LEVLINE_POST_WEEK4_PHASE1_2_FINDINGS.md](LEVLINE_POST_WEEK4_PHASE1_2_FINDINGS.md)  
**Frozen incumbent:** `F-ST-01-FROZEN-2026`  
**Priority:** Candidate A (`MKT-COMP-RESIDUAL-V1`) remains first. **No Alexandria data enters A, B, or C** without a separate, prior preregistration and independently verified chronology.

## 1. Decision and strict scope

**Decision: GO for small prospective, outcome-blind capture *design*; NO-GO for 2022–2025 historical challenger ingestion or any model feature authorization.**

This workstream is an append-only feasibility ledger, **not** Candidate A, a model, an implementation, a production feed, or a license to backfill old football states. This document specifies a minimal capture design only; it does not schedule or implement collection. One modeling candidate per chat. Leave the frozen winner accuracy, OOS population, baselines, feature identities, training and evaluation unchanged.

## 2. Verified Alexandria catalogue inventory (2026-10-07)

Discovery through the connected Firecrawl Alexandria catalogue is free. The following provider tools were found with published typed contracts and **5 credits per invocation**, **not per returned record** (`perRecord=false`). Pricing may change; re-query contracts and billing before activation. Catalogue contracts are evidence of tool availability, **not** a guarantee of historical data, source licensing, response freshness, or stable SLA.

| Provider / capability | Request and output shape | Source/time fields | Historical PIT suitability | Research value |
|---|---|---|---|---|
| `startwho-com/fantasy-sports-rankings/projections` | `position` QB/RB/WR/TE/K/DST/FLX/ALL required; `scoring` STD/HALF/PPR; optional `week`, `limit`. `players[]` includes site player ID, team, opponent, `game_kickoff_at`, `locked`, `projected_points`, `vegas_percent`, `props[]` (prop type, consensus line, odds, implied/EV estimate, market-backed points, per-book `line` and `over_odds`/`under_odds`), `bookmaker_points[]`. | Top-level `observed_at_ms`, human-readable `last_updated`, `source_url`; kickoff on each player. **No guaranteed per-book quote timestamps.** | **Not qualified**: contract says unavailable past/future weeks without published projections return `not_found`; a current response is not an archive of an earlier horizon. | Player-volume expectations; passing/rushing/receiving/TD quote consensus, cross-book dispersion, market-implied roles. |
| `startwho-com/fantasy-sports-rankings/injury_report` | Optional `team` or `position` (QB/RB/WR/TE only). `injuries[]`: player, team, position, `status_short` (Q/D/O/IR/PUP), body part, rank, `updated_at_ms`. | Top-level `observed_at_ms`, `updated_at_ms`, `source_url`; per-player status update millisecond epoch. | **Not qualified**: current-state list; a historical `updated_at_ms` does **not** establish that the returned full status snapshot was available at the earlier time. | Secondary cross-check; fantasy-focused only; **not** official NFL all-position injury coverage. |
| `nfl-com/sports-league-data/injury_report` | `season`, `season_type` PRE/REG/POST, `week`, optional `team` abbreviation/UUID. `reports[]`: player display/GSIS ID, team, position, injuries, `practice_days[]` with date + FULL/LIMITED/DIDNOT, `practice_status`, game designation OUT/DOUBTFUL/QUESTIONABLE. | `observed_at_ms` is **fetch time**; `report_date` is newest filing/practice date, **not a publication timestamp**; `source_url`, `weeks_available`. Contract expressly states the feed publishes no own update timestamp. | **Not qualified**: historical season/week retrieval, even if available, may expose the final report and cannot recreate the actual Wednesday/Thursday/T-120 view. | Authoritative, position-complete player participation and final game status, especially QB/OL/pass rush/secondary. |
| `nfl-com/sports-league-data/teams` | `season`, optional AFC/NFC; `teams[]` with club UUID, abbreviation, name and metadata. | `observed_at_ms`, `source_url`; current team metadata. | Identity/reference only; not a game-time state. | Resolve NFL `AZ` versus other providers' `ARI`, aliases, game/team joins. |

**Direct execution evidence:** a single small `startwho-com/.../projections` call for `week=5,position=QB,scoring=HALF,limit=2` succeeded. It returned `total_count=30`, `observed_at_ms=1791410068002`, `last_updated="Oct 7, 2026, 8:00 PM UTC"`, a Week-5 source URL, kickoff timestamp, and player-level props from multiple sportsbooks. This verifies the **current payload shape** only; it neither verifies past-week point-in-time history nor establishes that sportsbook subquotes were sampled simultaneously. The parallel attempt to execute the NFL injury provider hit the account's request/minute limit; that provider's shape is documented from its published contract/example rather than a successful live execution in this audit. **Do not claim an end-to-end NFL injury runtime test passed.**

**Cost/limits:** each of the four listed Alexandria capabilities advertises **5 credits per call**; discovery was free. The connected account's credit usage check before the sample showed 575 remaining out of a 1,000-credit billing allowance for the current period (2026-10-07 to 2026-11-07 UTC). Credits are shared across activities; this is a dated observation, **not** a standing budget or authorization for recurring spend. A rate-limit response in the smoke test showed the current plan's request/minute ceiling can be hit by parallel checks. Firecrawl publishes general pricing at https://www.firecrawl.dev/pricing ; Alexandria-specific catalogue contract pricing controls here. No paid upgrade, recurring job, or broad scrape was authorized. Retention, source redistribution, commercial-use terms, and provider contractual permissions remain **unverified**; confirm before any durable collector.

## 3. Incremental-information thesis (not a modeling finding)

LevLine already ingests **game-level** moneyline/spread market information, football rolling/EPA components, and separately governed prospective market/player-state research. Alexandria must NOT duplicate a game-side price in disguise.

1. **Potentially additive:** player-specific betting expectation (QB passing/rushing, RB volume, receiver target/yards, TD role); availability and practice trend by unit; information-arrival uncertainty; per-book disagreement for a named player. NFL.com supplies official practice participation covering linemen/defenders, not only fantasy skill positions.
2. **Likely redundant:** market-wide news already reflected in the contemporary game moneyline/spread, team strength and opponent-adjusted EPA, and existing official injury/roster sources; consensus player props may largely encode the *same* bookmaker information as game odds.
3. **Not established:** that StartWho's derived fantasy projection is independent of input props or existing LevLine props feeds. `vegas_percent` is a model provenance indicator, not an incremental-information test. Avoid duplicate book quotes/consensus and correlated-source double counting.
4. **Future independent test:** at the same frozen information horizon, compare available player-event/prop residual against the *contemporaneous* moneyline and incumbent F-ST with exact event/team/player joins; include baseline-only and source ablations; assess whether switches, not merely Brier or prop accuracy, improve. None of this is approved within Candidates A/B/C.

## 4. Minimal **proposed** prospective immutable snapshot (not implemented)

One capture envelope per **provider × capability × request filters × requested horizon × actual retrieval**. Store response hash and raw response in a restricted, append-only research-only store if source terms permit; do not place API secrets or licensed raw payloads in public Git history. Keep normalized child rows separately and preserve the envelope-to-child linkage.

```json
{
  "schema_version": "alexandria_pit_snapshot_v0_proposal",
  "snapshot_id": "<deterministic hash of source, filters, capture and payload>",
  "provider": "startwho-com",
  "capability": "fantasy-sports-rankings/projections",
  "provider_contract_version": "<catalogue version/contract hash>",
  "filters": {"week": 5, "position": "QB", "scoring": "HALF"},
  "nfl_season": 2026,
  "nfl_week": 5,
  "game_id": "<resolved NFL game id or null>",
  "player_id_source": "<source player id or null>",
  "player_gsis_id": "<verified join or null>",
  "scheduled_kickoff_utc": "<ISO8601>",
  "requested_cutoff_utc": "<ISO8601 T-120 or other preregistered capture horizon>",
  "request_sent_at_utc": "<ISO8601 UTC>",
  "response_received_at_utc": "<ISO8601 UTC>",
  "provider_observed_at_utc": "<derived from observed_at_ms or null>",
  "source_effective_date": "<provider filing date or null>",
  "source_updated_at_utc": "<only when supplied, else null>",
  "source_url": "<verbatim source url>",
  "status": "captured|not_found|failed|late|ambiguous_match",
  "source_payload_sha256": "<hash, if captured>",
  "source_payload_storage_ref": "<restricted immutable storage ref, if permitted>",
  "snapshot_has_postcutoff_information": null,
  "predictive_eligibility": "NOT_QUALIFIED"
}
```

**Child rows, only after a lawful future capture:** prop/player/book/market type, line, over/under American odds, quoted book, quote timestamp **null if not source-provided**, consensus type, derived implied/EV value with exact transformation metadata; injury GSIS ID, club, position, practice date and designation, declared game-status, practice-vs-fetch date. Explicitly store missing or unmatchable entities; do not infer `OUT` from omission. Preserve raw ID, alias map version, schedule/kickoff version, UTC timezone and response provenance.

**Ingestion design (proposal only):**
1. Research-only manual/low-rate pilot before any recurring capture; re-check terms and credit budget. Pin capability and contract version when supported.
2. Capture **no later than** the candidate's own preregistered cutoff. Set `request_sent_at` and `response_received_at` using an independent UTC clock. If response lands after cutoff or is a source-final report unavailable by that cutoff, **fail closed** for that horizon; do not backfill.
3. Use known game IDs from an immutable schedule source and explicit team/GSIS joining; avoid player-name-only joins. Site ID/team abbreviations are not universal.
4. Treat `last_updated`, player `updated_at_ms`, and NFL `report_date` as **different semantic clocks** from actual capture and from each sportsbook's quote time.
5. Store versioned raw and normalized hashes with errors, absent markets, duplicate books, observed coverage, rate-limit/credit receipt, and provenance flags; a later requery is a **new** snapshot, never a mutation of an earlier one.
6. Do not join late injury statuses, closing/settlement props, game results, or current injuries into earlier snapshots. Reject any apparent status or sportsbook subquote provably effective after the requested cutoff. Treat quote-age without per-book timestamps as unknown, not fresh.

No new workflow, API key, live collector, output artifact, model feature, or production import is part of this workstream.

## 5. Coverage, cost and leakage blockers

| Blocker | Consequence | Required independent evidence |
|---|---|---|
| StartWho weekly projection API returns `not_found` for unavailable past weeks | Cannot use today's call to backtest 2022–2025 prop states | Versioned source-native archive or contemporaneously captured historical records with timestamps and complete market books |
| NFL archive indexes old weeks but only current/final state is fetched | Historical game reports are **not historical publication snapshots** | Timestamped filing/revision history or actually preserved pre-cutoff captures |
| No per-sportsbook quote timestamp guaranteed | Per-book freshness and simultaneous consensus unknown | Book-level source quote timestamps or strict prospective capture + explicit unknown age |
| Differing injury clocks | Final Friday/Q status may be used incorrectly for Wednesday/T-120 predictions | Source filing clock + capture receipt at or before each frozen cutoff |
| Player-team joins, trades, ID/alias collisions | Entity leakage/misassignment | Versioned GSIS mapping and game-roster as-of |
| Source overlap with game market/existing props | False incremental signal and double counting | Baseline/residual ablations at identical horizon and same bookmaker universe |
| Variable prop coverage by player/position/week | Selection bias toward stars and active market names | Complete denominator (scheduled games/eligible players/books), structured missingness; never treat missing as zero |
| Firecrawl source license, frequency limits, cost | Ongoing ingestion may be prohibited or unaffordable | Provider permission/terms, documented cost ceiling, rate-limit pilot |

**Historical eligibility status:** 2022–2025 = **NOT VERIFIED**, not 0% coverage, not an implied complete archive. No historical prices/coverage were purchased or reconstructed. The current-week two-player smoke sample is **operational proof of shape only**, **not predictive evidence**.

## 6. Future qualification gate (must be separately authorized)

Alexandria becomes **eligible for a new, separately preregistered challenger** only when all of these are true:

- lawful retention/reuse and affordable repeatable collection verified;
- stable contracts, source provenance, actual capture and source-effective timestamps recorded;
- strict pre-kickoff horizon, books, timestamps and league/team/player joins audited with synthetic/fixture tests;
- coverage and missingness by week/team/position/market demonstrated prospectively;
- data genuinely distinct from existing player feeds and game-level market state;
- a candidate ID, feature registry, comparator, ablations, hyperparameter policy, evaluation dates and sample-size/stop rules frozen **before** opening outcomes;
- any proposed historical backtest has independently verifiable contemporaneous source snapshots; otherwise prospective-only shadow and untouched holdout.

Only then consider a **new** player-state/market-quality residual workstream. No silent Alexandria input to Candidate A, `MARGIN-RESIDUAL-WIN-V1`, or `EARLY-STATE-SHRINKAGE-V1`. Preserve existing A/B/C preregistration unchanged; no retroactive improvement claims.

## 7. Handoff / stop condition

**Now:** Candidate A remains the sole immediate modeling experiment. Alexandria feasibility documentation is complete as a separate workstream; no further Alexandria calls required in the Candidate A chat. **Next permitted Alexandria step:** an independently approved *research-only* one-week low-rate prospective capture pilot, after source-terms and budget verification, with no candidate fitting or official predictions. One candidate per modeling chat.

**Unchanged:** frozen F-ST, Sunday Signal, official historical accountability, ATS grading, production pipeline, Candidate A's feature list, coefficients/regularization/architecture, test population and evaluation protocol; Candidates B/C future preregistrations; 2026 outcome firewall.
