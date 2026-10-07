# Phase 4 D — Alexandria independent viability addendum (2026-10-07)

**Scope:** No A/B/C changes, no scheduled calls, no credit-consuming replays. Supersedes no prior finding in `research/LEVLINE_ALEXANDRIA_PIT_FEASIBILITY_2026_10_07.md`.

## Evidence carried forward and not exaggerated

The provider catalogue previously identified these capabilities at **5 credits/invocation at that inspection time**: `startwho-com/fantasy-sports-rankings/projections`, `startwho-com/fantasy-sports-rankings/injury_report`, `nfl-com/sports-league-data/injury_report`, `nfl-com/sports-league-data/teams`. Current credit pricing/remaining allowance must be rechecked before any fresh request. Only a **two-player Week 5 StartWho projection payload** was successfully smoke-tested, not a complete weekly universe. NFL.com live injury invocation was rate-limited, therefore its example schema is a contract claim, not operational validation.

Time semantics: StartWho top-level `observed_at_ms` is acquisition time, `last_updated` is page-level and per-book quote timestamps are not guaranteed. `props[].consensus_line` and book-level lines/odds might add player-role information beyond game market, but book quote age and dependence on consensus fantasy projections remain unknown. NFL.com `report_date` is a filing date; its `observed_at_ms` is retrieval, not publication or revision history. Historical week queries cannot establish an older Wednesday/T-120 state from a final Friday snapshot. StartWho injury status is fantasy-skill limited, unlike broader official injury practice reports. NFL `teams` is an identity mapper, not a chronological playing-state feed.

## Feasibility decision table

| Gate | Evidence | Decision |
|---|---|---|
| Data fields and potential signal | Contract shows lines, odds, props, fantasy projection and official injury/practice designation | DESIGN_ONLY |
| Per-book quote clock | No guaranteed original provider quotation time | BLOCKED |
| Prior-week publication history | No original historical revision/point-in-time archive established | BLOCKED |
| Live rate limits | Previous NFL.com request hit request/minute limit | BLOCKED_FOR_RELIABLE_PILOT |
| Cost | Previously observed 5 credits per tool call; not a standing budget | NO_RECURRING_SPEND |
| Reuse/retention/licensing | Terms for response retention/derived redistribution unverified | BLOCKED |
| Relative information to existing LevLine input | Possible player-specific roles, but high market overlap | HYPOTHESIS_ONLY |
| Candidate C architecture | Frozen features and weights | NO_CHANGE |

## Minimal future pilot (not authorized by this addendum)

One independently timestamped provider-request envelope, provider response SHA, source URL/contract version, filters, source clocks as separately typed, kickoff/schedule identity, per-player IDs and quote timestamp or explicit null; restricted storage only after confirming rights. Include full scheduled-game denominator and structured missingness by position/team and failed request. A future decision needs an inexpensive authenticated live T-120 sample with a verified provider clock, quote freshness assessment, rights to retain normalized data, and a separately preregistered **new** challenger. No use of Alexandria within C. Free Firecrawl catalogue discovery and current balance retrieval were performed on 2026-10-07; no provider payload was executed or purchased during this addendum. Earlier StartWho sample receipts remain the sole provider execution evidence.

**Decision:** `ALEXANDRIA_PROSPECTIVE_FEASIBILITY_ONLY`; not an official-lock adapter, not historical PIT support, not a predictive improvement.

## Fresh, non-billable catalogue/credit verification — 2026-10-07

A catalogue semantic search returned the current NFL.com injury-report, StartWho projections, and StartWho injury-report capabilities, all advertising 5 credits per call, perRecord=false. The catalogue version was `sha256:7e1ad92d663943585cf2bbf49ceb656acde450aaeab203ef2c0b457812de620b`. A direct request for fully qualified capability IDs was rejected as invalid; the semantic catalogue lookup succeeded. The authenticated team's remaining credits at this check were **563 of 1,000** for 2026-10-07 21:33 UTC to 2026-11-07 21:33 UTC. Both discovery and balance checks incurred **0 credits**. No fresh live provider execution occurred; current credit balance can fluctuate for unrelated usage and creates no future spending authorization.
