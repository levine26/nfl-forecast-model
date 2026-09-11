# LevLine Data Source & Rights Matrix

Status: **research governance**. This document does not authorize a new production data source, probability feature, lock rule, or public redistribution right.

## Decision rule

A source is not production-ready merely because it is technically accessible. LevLine separates six gates: **identity**, **timestamp semantics**, **point-in-time reproducibility**, **reliability/coverage**, **cost/operability**, and **rights/redistribution**. A source must pass the gates required by its intended use before it can cross the research firewall.

| Source | Family | Intended LevLine role | Point-in-time status | Cost / operating note | Rights status | Current decision |
|---|---|---|---|---|---|---|
| nflverse `games.csv` | Public football dataset | Schedule/results/Elo scaffold; existing moneyline benchmark | Historical moneylines are useful as a late/closing benchmark, not a matched T-minus lock feed | Existing public upstream; game/schedule data are documented as refreshing about every five minutes in season | Existing project source; preserve attribution and review underlying-source restrictions before expanding redistribution | **Keep in production for existing use. Treat market as opaque upstream benchmark.** |
| The Odds API, US `h2h` | Sportsbook aggregator | Prospective multi-book moneyline + lock-horizon research | Good for forward T-120/T-90/T-60/T-45/T-30/T-25/T-15 capture | One market × one region costs one usage credit; provider currently advertises 500 credits/month on Starter. One request can service an entire kickoff cluster. | API access does not by itself establish publication/redistribution rights; source-specific terms review remains required | **Preferred first multi-book research feed. Not production-authorized.** |
| FanDuel | Sportsbook | Component of sportsbook consensus | Timestamped prospectively through an approved feed | Included when returned by aggregator | Inherits feed contract; no direct scraping assumption | **Research component only.** |
| DraftKings | Sportsbook | Component of sportsbook consensus | Timestamped prospectively through an approved feed | Included when returned by aggregator | Inherits feed contract; no direct scraping assumption | **Research component only.** |
| BetMGM | Sportsbook | Component of sportsbook consensus | Timestamped prospectively through an approved feed | Included when returned by aggregator | Inherits feed contract; no direct scraping assumption | **Research component only.** |
| Polymarket | Prediction exchange | Independent exchange-information candidate | Requires event-level timestamp/liquidity audit | Public API is technically available | API accessibility confirmed; persistence/redistribution review still required | **Keep separate from sportsbook consensus; research only.** |
| Kalshi | Prediction exchange | Possible independent exchange-information candidate | Not yet audited for LevLine | Technically possible only after source-policy clearance | Specific developer data-use/storage/redistribution review required | **Exclude from automated collection for now.** |
| NFL.com official injury reports | Availability | Prospective player-impact/reference evidence | Historical rendered pages alone do not prove exact T-minus row state/revisions or stable-ID mapping | Public reference | Automated storage/redistribution needs separate review | **Prospective reference/explainability only.** |
| Sportradar Weekly Injuries v7 | Availability | Leading candidate for qualified historical + prospective availability | Promising fields, but requires credentialed revision-history and stable-ID crosswalk audit | Commercial | Contract must explicitly cover intended storage/research/publication use | **Best availability source to audit next; not yet qualified.** |
| SportsDataIO injuries | Availability | Secondary availability candidate | Historical revision reconstruction and GSIS crosswalk not yet proven | Commercial | Contract review required | **Secondary audit candidate.** |

## Sportsbook consensus contract

The sportsbook research signal must preserve the individual bookmaker rows. LevLine de-vigs each two-way moneyline independently, records the bookmaker identity and provider update timestamp, and then derives a robust consensus in logit space. Missing books are explicit. The consensus records source count, constituent names, and freshness. No single bookmaker is silently labeled “the market.”

The existing nflverse moneyline remains a separate comparator because its bookmaker-level provenance is not available in the production row. This prevents accidental self-comparison if the upstream value already contains an unknown consensus.

## Refresh cadence economics

The prospective collector is designed around **information arrival**, not around rerunning the whole football model. Football/PURE is held fixed between substantive football-data updates; near kickoff, only the market feed is refreshed and the frozen F-ST equation is rescored.

The current research window is T-65 through T-10, checked every five minutes. A local kickoff gate runs before dependency installation or an external odds call. With one `h2h` market in one region, each actual call costs one provider usage credit. A normal kickoff cluster therefore needs at most roughly twelve scheduled observations across that window, while invocations outside a due window make no odds request. Actual quota headers are persisted and collection stops at a reserve rather than assuming a monthly allowance will always be sufficient.

This cadence is a research design, not a production lock change. The official lock remains T-120 until matched-horizon evidence supports another horizon.

## Prediction-exchange policy

Sportsbooks and prediction exchanges are different information-generating systems. Polymarket or a future-cleared Kalshi feed must not be inserted into the sportsbook consensus by default. Each exchange requires an event-identity map plus liquidity, bid/ask, depth, stale-quote, and resolution-rule controls. Only after an exchange signal demonstrates incremental out-of-sample information at matched horizons should a separately pre-registered ensemble test be considered.

## Availability / player-impact policy

The Expected Lineup Impact Engine already exists behind the research firewall. Availability inputs must be genuinely pregame, stable-ID mapped, and associated with a defensible information horizon. Actual current-game snaps, participation, scores, or hindsight-based final status are prohibited substitutes.

No complete 2022-2025 historical availability source is presently qualified for a player-derived probability feature. The player-impact system therefore remains useful for explainability and prospective capture even while probability integration stays prohibited.

## Current decisions

1. **Use The Odds API as the first prospective multi-book sportsbook research feed**, subject to credentials and source-rights review; do not replace production nflverse market yet.
2. **Preserve individual FanDuel, DraftKings, BetMGM and other returned book observations** before calculating any consensus.
3. **Keep Polymarket separate** as an exchange research candidate.
4. **Do not automate Kalshi collection/storage** until its relevant data-use rights are specifically cleared.
5. **Audit Sportradar first for player availability** if credentialed access is available; SportsDataIO is the secondary candidate.
6. **Do not select a T-25 lock from historical closing odds.** Use the prospective matched-horizon ledger and require an uncertainty-supported improvement in probability quality plus acceptable missing/stale-data performance.

## References

- nflverse data access and update schedule: https://nflreadr.nflverse.com/ and https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html
- nflverse game data dictionary: https://github.com/nflverse/nfldata/blob/master/DATASETS.md
- The Odds API v4 usage/response documentation: https://the-odds-api.com/liveapi/guides/v4/
- The Odds API plans: https://the-odds-api.com/
- Polymarket developer access: https://help.polymarket.com/en/articles/13364254-does-polymarket-have-an-api and https://docs.polymarket.com/
- Kalshi developer/regulatory materials: https://docs.kalshi.com/ and https://kalshi.com/regulatory/agreement

The references establish technical/public documentation only. This matrix intentionally does not infer a redistribution license where one has not been separately verified.
