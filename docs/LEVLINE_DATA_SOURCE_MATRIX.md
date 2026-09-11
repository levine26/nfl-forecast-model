# LevLine Data Source & Rights Matrix

Status: **research governance**. This document does not authorize a new production data source, probability feature, lock rule, or public redistribution right.

## Decision rule

Technical accessibility is not permission. LevLine treats **identity**, **timestamp semantics**, **point-in-time reproducibility**, **coverage/reliability**, **cost/operability**, and **rights/redistribution** as separate gates. A source must pass the gates required for its specific use before crossing the research firewall.

| Source | Family | Intended role | Timing / coverage | Rights posture | Current decision |
|---|---|---|---|---|---|
| nflverse game/schedule data | Public football dataset | Schedule/results/Elo scaffold; existing opaque moneyline benchmark | Game/schedule data refresh about every five minutes in season; current injury dataset has no 2025 coverage | Existing project source; preserve attribution and review underlying-source restrictions before expanding redistribution | **Keep existing production use; market remains opaque upstream benchmark.** |
| The Odds API US `h2h` | Sportsbook aggregator | Prospective multi-book moneyline and lock-horizon research | Near-kickoff collector retains per-book timestamps and provider quota headers | API access does not itself grant public redistribution | **Preferred first multi-book research feed; not production-authorized.** |
| FanDuel / DraftKings / BetMGM via approved aggregator | Sportsbooks | Components of sportsbook consensus | De-vig and timestamp each book separately | Inherits feed contract; no direct-site scraping assumption | **Research components only.** |
| Polymarket | Prediction exchange | Independent exchange-information candidate | Requires event mapping plus liquidity/depth/staleness controls | API availability does not settle persistence/redistribution | **Keep separate from sportsbook consensus; research only.** |
| Kalshi | Prediction exchange | Possible independent exchange signal | Not yet cleared for LevLine collection/storage | Specific developer/data-use review required | **Exclude pending rights review.** |
| NFL.com injury reports | Availability | Prospective reference and explainability | Current report useful; rendered history alone does not establish exact T-minus revision state or stable IDs | Public reference; automated persistence/redistribution requires separate review | **Explainability reference only.** |
| Sportradar NFL Weekly Injuries v7 | Availability | Leading historical/prospective availability audit candidate | Weekly Injuries exposes player GUID, practice/injury status and `status_date`; NFL historical feeds are documented back to 2000 REG/PST | Commercial contract must cover intended storage, modeling and publication | **Audit first; not yet qualified.** |
| SportsDataIO injuries | Availability | Secondary availability candidate | Historical revision reconstruction and stable-ID crosswalk remain unproven | Commercial contract required | **Secondary audit candidate.** |
| NFL Next Gen Stats via nflverse | Advanced player statistics | Research player context | nflverse documents nightly player-week NGS refreshes during season, subject to upstream availability | Confirm upstream/redistribution terms before public player-level display | **Research only.** |
| PFR-derived data via nflverse | Advanced player statistics | Snap counts / advanced-stat research | nflverse documents multiple daily snap refreshes and daily advanced-stat refreshes | Do not assume direct automated access or redistribution rights | **Research only.** |
| PFF Pro API | Advanced player statistics | Potential private research features | Paid API/CLI access is currently offered | Current consumer API terms limit use to personal use and do not grant public distribution/commercial use | **Not eligible for public/commercial LevLine use under consumer terms.** |

## Sportsbook consensus contract

The research sportsbook signal preserves constituent books. Each two-way moneyline is de-vigged independently, bookmaker identity and update timestamp are retained, and only then is a robust consensus calculated. Missing books, source count, constituents and freshness remain explicit. No single book is silently relabeled as “the market.”

The nflverse moneyline remains a separate comparator because its bookmaker-level provenance is not available in the production row. This avoids accidental self-comparison if the upstream value is itself an unknown consensus.

## Near-kickoff research cadence

The prospective collector targets information arrival rather than rerunning the football stack. PURE remains fixed between substantive football-data changes; near kickoff only the market feed is refreshed and the frozen F-ST equation can be rescored in research.

The collector uses a local due-game gate before external requests and persists to the off-main research ledger. Runtime provider quota headers, not a hard-coded plan assumption, control whether collection continues. The official lock remains T-120 unless matched-horizon evidence later supports another rule.

## Exchange policy

Prediction exchanges are not sportsbooks. Polymarket, and any future-cleared Kalshi feed, must remain a separate information family with event-identity, liquidity, bid/ask, depth, stale-quote and resolution-rule controls. No exchange is folded into sportsbook consensus by default.

## Player / availability policy

The Expected Lineup Impact Engine and Impact Monitor are research/explainability layers. Availability used for a probability feature must be stable-ID mapped, genuinely known by the tested horizon and point-in-time reproducible. Actual current-game snaps, participation or hindsight-based inactive status are prohibited proxies.

The current open-source stack still lacks a complete 2022-2025 historically qualified availability source. nflverse explicitly reports that its injury source ended after 2024 and that there is presently no 2025 injury data. This is why current NFL.com injury context may be displayed conservatively while probability integration remains prohibited.

Sportradar is the strongest availability audit candidate identified so far because its current NFL Weekly Injuries documentation exposes stable player GUIDs, injury/practice status and a `status_date`, and its historical-data documentation says season-addressable NFL feeds extend back to 2000 for regular/postseason data. That still does **not** prove an exact historical T-120 revision snapshot: a credentialed audit must establish whether later revisions can be reconstructed without hindsight.

## Advanced player data

nflverse can automate useful NGS and PFR-derived research data, but source-level publication rights still matter. Sports Reference’s terms restrict unauthorized automated access, so LevLine should use already-approved/contracted data paths rather than building a direct scraper.

PFF now offers API/CLI access with a paid PFF Pro tier, but its current consumer API terms describe the license as personal-use and expressly withhold commercial/public-distribution rights. PFF therefore may be technically attractive for private experimentation but is not an eligible public LevLine source under those consumer terms; broader rights would require a separate written agreement.

## Current decisions

1. Keep the production F-ST market source and T-120 lock unchanged while the prospective multi-book ledger grows.
2. Use The Odds API as the first multi-book research feed and preserve constituent books before consensus.
3. Keep prediction exchanges separate from sportsbook consensus; Polymarket remains research-only and Kalshi remains excluded pending rights review.
4. Audit Sportradar first for historically reproducible player availability; treat current NFL.com injury reports as explainability context only.
5. Use NGS/PFR-derived data only through appropriately reviewed data paths; do not create a direct Sports Reference scraper.
6. Treat PFF consumer API data as ineligible for public/commercial LevLine use absent broader written rights.
7. Do not promote any player-impact or availability feature from this matrix. Source qualification and model qualification are separate decisions.

## Evidence reviewed

- nflverse data update schedule and current injury-data coverage.
- Sportradar NFL Weekly Injuries v7 and NFL historical-data documentation.
- PFF current subscription/API description and Terms of Use.
- Sports Reference / Stathead terms for automated access.
- Existing provider documentation already recorded in `research/data_source_governance.json` for The Odds API, Polymarket and Kalshi.

This matrix is deliberately conservative: when a license, historical revision property or redistribution right is not proven, the status remains pending/restricted rather than inferred from technical accessibility.
