# LevLine Data Source & Integrity Matrix

Status: **research governance**. This document does not authorize a new production data source, probability feature, lock rule, or model promotion.

## Decision rule

LevLine qualifies a source **only on the data and integrity of the source itself**: identity quality, timestamp semantics, point-in-time reproducibility, coverage, missingness, reliability, publication/persistence timing, availability, and reproducibility. Licensing, usage-rights, and redistribution information may be retained as metadata, but **never blocks technical qualification** and never changes a technical pass/fail decision.

Active automated research separately follows the existing **$0 cost policy**. Production remains a separate explicit authorization decision: a technically qualified research source does not automatically become a production dependency.

| Source | Family | Intended role | Data-integrity status | Rights metadata (non-blocking) | Current decision |
|---|---|---|---|---|---|
| nflverse game/schedule data | Public football dataset | Schedule/results/Elo scaffold; existing opaque moneyline benchmark | Frequent in-season refresh; market provenance remains opaque and not horizon-matched | Attribution/source metadata retained | **Keep existing production use; market remains opaque upstream benchmark.** |
| The Odds API US markets | Sportsbook aggregator | Prospective multi-book moneyline/spread/total capture | Prospective only; retain per-book timestamps, freshness, source count and quota state | Provider metadata retained | **Preferred first multi-book research feed; not production-authorized.** |
| FanDuel / DraftKings / BetMGM via aggregator | Sportsbooks | Components of sportsbook consensus | Each book must be de-vigged and timestamped independently | Feed metadata retained | **Research components only.** |
| Polymarket | Prediction exchange | Independent exchange-information candidate | Event mapping, liquidity/depth, staleness and point-in-time audit required | Terms metadata retained | **Separate research family; not sportsbook consensus.** |
| Kalshi | Prediction exchange | Possible independent exchange signal | Public market-data API candidate; event identity, liquidity, timestamp and coverage audit pending | Terms metadata retained | **Research candidate pending data-integrity audit.** |
| `edgecdec/declan-fantasy-football` Sleeper archive | Availability / player state | 2026 point-in-time player-state and prospective shadow research | **Verified for 2026-only scope.** Archive starts 2026-02-01; all-position audit requires >=99.5% identity/schema gates; commit time is conservative availability bound | Repository/API metadata retained | **Qualified for 2026 point-in-time/shadow research; cannot reconstruct 2025.** |
| NFL.com injury reports | Availability | Prospective reference and explainability | Current reference useful; rendered history alone does not prove stable IDs or exact T-minus revision state | Reference metadata retained | **Explainability/reference until identity + PIT audit passes.** |
| Sportradar Weekly Injuries | Availability | Potential historical/prospective availability feed | Stable IDs/status fields look promising, but exact revision-as-of semantics require proof | Commercial metadata retained | **Inactive under $0 policy; cataloged as technical candidate only.** |
| SportsDataIO injuries | Availability | Secondary availability candidate | Historical revision reconstruction and stable-ID crosswalk remain unproven | Commercial metadata retained | **Inactive under $0 policy.** |
| NFL Next Gen Stats via nflverse | Advanced player statistics | Research player context | Weekly observed data; only prior-completed-game rows may enter a forecast | Source metadata retained | **Research only pending PIT/incremental-value audit.** |
| PFR-derived data via nflverse | Advanced player statistics | Snap counts / advanced-stat research | Refreshable observed data; chronology and missingness must be enforced | Source metadata retained | **Research only pending PIT/incremental-value audit.** |
| FTN charting via nflverse | Manual charting | Prior-completed-game process research | 2022+ and preregistered for chronology-aware testing; never same-game pregame information | CC BY-SA metadata retained | **Qualified research candidate under preregistered process test.** |
| SIS / SumerSports / raw NGS / PFF Pro | Advanced / tracking | High-value advanced-player research candidates | Some feeds lack a reproducible automated interface; others are paid | Rights metadata retained but non-blocking | **Not active in the current $0 pipeline; technical qualification remains distinct.** |

## Sportsbook consensus contract

The research sportsbook signal preserves constituent books. Each two-way moneyline is de-vigged independently, bookmaker identity and update timestamp are retained, and only then is a robust consensus calculated. Missing books, source count, constituents and freshness remain explicit. No single book is silently relabeled as “the market.”

The nflverse moneyline remains a separate comparator because its bookmaker-level provenance is not available in the production row. This avoids accidental self-comparison if the upstream value is itself an unknown consensus.

## Near-kickoff research cadence

The prospective collector targets information arrival rather than rerunning the football stack. PURE remains fixed between substantive football-data changes; near kickoff only the market feed is refreshed and the frozen F-ST equation can be rescored in research.

The collector uses a local due-game gate before external requests and persists to the off-main research ledger. Runtime quota evidence controls whether collection continues. The official production lock remains T-120 unless matched-horizon evidence later supports another rule and an explicit production change is authorized.

## Exchange policy

Prediction exchanges are not sportsbooks. Polymarket, Kalshi, and any future exchange feed remain a separate information family with event-identity, liquidity, bid/ask, depth, stale-quote and resolution-rule controls. No exchange is folded into sportsbook consensus by default.

## Player / availability policy

The Expected Lineup Impact Engine and Impact Monitor remain research/explainability layers. Availability used quantitatively must be stable-ID mapped, genuinely known by the tested horizon, and point-in-time reproducible. Actual current-game snaps, participation, or hindsight-based inactive status are prohibited proxies.

The verified Sleeper archive is the first active zero-cost player-state source for 2026 point-in-time work. Its history begins February 1, 2026, so it **does not** unlock a 2022-2025 historical availability backtest. That limitation is a coverage fact, not a rights decision.

No zero-cost source currently supplies qualified 2025 point-in-time injury state for a full 2022-2025 availability backtest. Until such data exists, historical availability model fitting fails closed for that scope while 2026 prospective/shadow collection proceeds.

## Advanced player data

Advanced-player sources are ranked on chronology, identity, coverage, missingness, reliability and reproducibility. Rights/license fields are descriptive metadata only. Under the active $0 research constraint, paid feeds are not automated even if technically promising; this is an operating-budget policy, not a technical data-quality judgment.

FTN charting through nflverse remains attractive because it is available at $0 and provides prior-completed-game process variables. Same-game charting is never used as pregame information. nflverse NGS/PFR-derived data may be studied only with explicit chronology and missingness controls.

## Current decisions

1. Keep production F-ST semantics and the T-120 lock unchanged while research evidence accumulates.
2. Use The Odds API free tier as the first prospective multi-book research feed; preserve constituent books and timestamps.
3. Keep exchanges separate from sportsbook consensus; qualify them on event identity, timing, liquidity and reproducibility—not rights.
4. Use the verified Sleeper archive as the first active zero-cost availability/player-state source for **2026-only** point-in-time and shadow work.
5. Do not claim 2025 reconstruction from the Sleeper archive; no zero-cost availability source currently unlocks a 2022-2025 availability backtest.
6. Keep paid advanced/availability feeds inactive under the $0 research policy, while recording their technical potential separately.
7. Do not promote any player-impact, availability, market, weather, or advanced-player feature solely because its source is technically qualified. Source qualification and model qualification are separate decisions.
8. Completed 2026 outcomes remain prohibited for choosing model fields, coefficients, architecture, hyperparameters, or thresholds.

The operative rule is simple: **rights never determine technical source qualification; the data does.**
