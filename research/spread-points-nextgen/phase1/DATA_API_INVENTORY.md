# Phase 1 — Data/API Inventory

**Status:** research inventory / no source promotion  
**Audited repository main:** `e63fd396e1ae37fc63a4085e380ba52e0412dc74`  
**Binding operating constraint:** active research cost ceiling is $0.

A source existing in code is not the same as being configured, point-in-time reconstructable, technically qualified, used by the current score model, or production-authorized. Phase 1 keeps those states separate.

## 1. Core football data

| Source / provider | Role | Cost/auth | Coverage & timing | Current state | Score-model use | Phase 2 suitability |
|---|---|---|---|---|---|---|
| nflverse `games.csv` | schedule, teams, scores, rest, market fields, venue metadata, QB/coach fields | free/open | multi-season through live 2026; frequent refresh | active | schedule/results/rest scaffold; results feed targets; QB/coach fields are not score features | strong for stable schedule metadata; historical market/QB fields need PIT caution |
| nflverse / nflreadpy PBP | EPA, success, pass/rush process | free/open | historical + live season subject to publication lag | active with fail-closed newest-season fallback | **direct** via lagged team efficiency/form | strong for prior-completed-game research |
| nflverse team stats | team aggregates | free/open | multi-season, best effort | loaded best-effort | not directly consumed by current score feature builder | research candidate |
| pregame Elo derived in repo | dynamic strength | internal | sequential from schedule/results | active | **direct** | strong baseline/feature family |
| schedule venue / roof / division | game context | free/open | historical schedule rows | available | not direct score feature | suitable for stable metadata diagnostics |
| schedule temperature / wind | realized/historical weather fields | free/open | historical schedule rows | available in source | not direct score feature | diagnostic only unless pregame forecast timing is reconstructed |

### Core chronology note

The team-state feature builder shifts performance one completed game before calculating rolling features. Current-game PBP therefore does not enter that same game's pregame feature row.

The schedule also contains fields such as `home_qb_id`, `away_qb_id`, coach, temperature, and wind. Their presence in a final historical schedule row does **not** prove they were known at the simulated pregame decision time.

## 2. Player, availability, and personnel sources

| Source | Cost/auth | Historical scope | PIT / identity status | Current use | Phase 1 decision |
|---|---|---|---|---|---|
| nflverse depth charts | $0 | timestamped from 2025+ | `dt` timestamp; GSIS IDs; latest snapshot <= decision time | research foundation | qualified research with constraints; depth rank is not injury status |
| 2025 availability composite | $0 | 2025 Weeks 1–22 | 6,064/6,068 player-week rows resolve; matched practice state known before T-120; four fail closed | research only | **qualified for 2025 practice state only**; not a unified 2022–25 source |
| NFL.com official injury reports | $0 | current + historical pages used in 2025 composite | official, but rendered pages alone are not revision-aware history | explainability + composite component | context/research; standalone historical final-status feature unauthorized |
| 2026 NFL.com injury snapshot archive | $0 | prospective 2026 | append-only raw and normalized receipts | research only | good prospective evidence; no historical backfill |
| Sleeper historical snapshot archive | $0 | starts 2026-02-01 | Git commit is conservative persistence bound; identity gates required | 2026 research | qualified for 2026 shadow research only |
| nflverse rosters | $0 | multi-season | stable IDs/crosswalks where populated | research/context | continuity/identity candidate |
| nflverse NGS weekly | $0 | roughly 2016+ | observed weekly; only prior-completed-game values allowed | explainability/research | lagged research candidate |
| nflverse PFR advanced | $0 | multi-season subject to stat family | historical observed data; publication timing still matters | best-effort context | research candidate |
| FTN charting via nflverse | $0 | 2022+ | prior-completed-game only | research | technically qualified research candidate |
| nflverse participation | $0 | 2016+ loader | 2023+ publication can be postseason-late, limiting in-season reconstruction | research | constrained historical use |
| DynastyProcess IDs | $0 | current + Git history | identity only | crosswalk | never status evidence |
| direct raw NGS tracking | no $0 reproducible feed | proprietary | unavailable to current pipeline | inactive | high theoretical value; unavailable |
| SIS / SumerSports / PFF | paid/commercial | potentially rich | no active $0 reproducible LevLine interface | inactive | data-gap candidates only |
| Sportradar / SportsDataIO injuries | paid/commercial | potentially historical | revision-as-of semantics not proven here | inactive | not active under $0 policy |

### Reusable 2025 availability evidence

The qualified 2025 composite is the only current historical availability slice strong enough for Phase 1 residual diagnostics. It authorizes final practice state known by T-120, **not** hindsight game status, realized snaps, or actual participation.

## 3. Market data

| Source | Role | Cost/auth | Timing | Current runtime state | Use |
|---|---|---|---|---|---|
| nflverse schedule moneyline/spread/total | historical benchmark + current scaffold | $0 | exact historical bookmaker/capture horizon opaque | active | market benchmark; current official F-ST uses moneyline-derived probability |
| `market_t120.py` | same-horizon selector from LevLine run history | internal | latest valid market snapshot at or before T-120 | active research utility | horizon-controlled research |
| The Odds API free tier | prospective multi-book h2h/spread/total | free tier; credential referenced | request + bookmaker timestamps | **latest inspected status: configured but HTTP 401 Unauthorized; market snapshot ledger empty** | research only |
| FanDuel / DraftKings / BetMGM via aggregator | constituent books | via free aggregator path | per-book timing when collector works | blocked by current aggregator authorization error | research-only components |
| Polymarket | exchange probability | public API | prospective mapping/liquidity/timestamp audit needed | candidate | separate from sportsbook consensus |
| Kalshi | exchange probability | public API candidate | event mapping/liquidity/timestamp audit needed | candidate | separate from sportsbook consensus |

### Credential status

The repository references a market API credential through GitHub Actions and the research status file records that a key is configured. The latest off-main market capture status nevertheless reports HTTP 401 Unauthorized and an empty `market_snapshots.csv`. Secret values are not reproduced in Phase 1 artifacts.

## 4. Weather and venue data

| Source | Role | Cost | PIT status | Current runtime state | Decision |
|---|---|---|---|---|---|
| NWS API | prospective weather forecast snapshots | $0 | retrieval/provider timestamps preserved | collector implemented | research only |
| Open-Meteo archived/single runs | historical forecast reconstruction | $0 within open limits | model initialization is not public availability; lag must be enforced | qualified research candidate | suitable only under run-availability contract |
| game-specific venue resolver + Wikidata | map game to exact venue coordinates | $0 | game-specific receipt required | current ledger contains unresolved venues, including inspected SoFi example | blocks weather capture for unresolved games |

The latest inspected weather status is `unavailable`: one due horizon, zero captured, one unavailable. Existing weather ledger rows are predominantly fail-closed receipts stating that a qualified game-specific venue receipt was unavailable. This is a data-foundation blocker, not evidence that weather lacks predictive value.

## 5. News, media, and official-report context

Current source policy permits official team sites plus selected major reporting domains for attributable context. These sources feed explanation/current-state workflows, not the numerical score regressions.

News should not become a historical numeric feature unless each item can be tied to a reproducible publication timestamp at or before the simulated decision horizon.

## 6. Existing advanced/context code versus actual forecast use

The repository contains substantial context infrastructure for:

- current starting QBs and opponent history;
- career QB ledgers;
- NGS passing profiles;
- injuries and practice status;
- prior player usage;
- depth charts;
- weather capture;
- market horizon capture;
- media/context evidence.

Phase 1 confirms that this infrastructure is **not automatically predictive input**. The current independent margin/total regressions still use the Core team/Elo/rest feature set only.

## 7. Point-in-time classification

### Safe as currently used

- prior completed-game PBP aggregated and shifted before the current row;
- sequential pregame Elo;
- schedule identity, opponent, game date, site/home-away;
- rest differential;
- completed prior-game outcomes.

### Conditionally safe

- depth chart snapshots with `dt <= decision_time`;
- 2025 qualified practice state under its exact T-120 contract;
- prior-week NGS / FTN / advanced data after publication timing is satisfied;
- prospective market/weather snapshots with immutable retrieval timestamps;
- rosters only when an as-of snapshot is preserved.

### Unsafe without additional proof

- final historical QB IDs used as a proxy for what was known at T-120;
- final injury/game status learned after the tested horizon;
- realized current-game snaps/workload/starter identity;
- realized weather used as if it were a pregame forecast;
- later-corrected depth charts;
- current roster endpoints projected backward in time;
- news without preserved publication timestamps;
- historical nflverse market lines relabeled as a specific T-minus horizon.

## 8. Missing-source behavior

Phase 1 requires missingness to remain explicit.

Do not:

- call a missing injury row “healthy”;
- call a missing QB-state row “stable starter”;
- backfill historical weather with realized conditions;
- silently substitute current roster/depth data for old snapshots;
- impute a sportsbook line merely to increase a paired benchmark sample;
- treat failed API collection as “no market movement.”

## 9. David Sasser external comparator

davidsasser.com is included in the external-source inventory at the user's request.

The current public college-football board exposes, game by game:

- model-projected team scores;
- a model projected line;
- opening market line;
- current market line;
- ATS pick;
- straight-up and ATS record tracking.

That structure is directly relevant to LevLine's score-versus-market architecture because it cleanly distinguishes a model-generated scoring view from the betting-market comparison layer. The public pages inspected in Phase 1 do not disclose enough model specification, input provenance, walk-forward protocol, or point-in-time methodology to use Sasser's reported record as reproducible validation evidence. Phase 2 should study any public source code or methodology that can be independently verified.

## 10. Data/API priorities carried to Phase 2

1. Repair prospective multi-book market collection before relying on it for horizon experiments.
2. Finish exact game-venue resolution so weather capture can actually produce qualified snapshots.
3. Preserve the 2025 availability composite and 2026 injury/depth archives; do not falsely bridge the 2022–2024 gap.
4. Prefer lagged, stable-ID player/QB/scheme variables that can be reconstructed point-in-time.
5. Keep market, player-state, and weather source qualification separate from model-feature qualification.
6. Keep paid sources cataloged only as data-gap options under the current $0 constraint.
