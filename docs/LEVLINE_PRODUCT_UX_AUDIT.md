# LevLine / Sunday Signal — Product UX Research Phase 1

Status: **research only**. This document does not change forecast semantics, the production model, the T−120 lock, or publication rules.

## Product thesis

Sunday Signal should feel like a trustworthy forecast product, not a sportsbook screen and not a model-debugging console.

The default experience should answer four questions in seconds:

1. Who does LevLine favor?
2. How likely is that outcome?
3. How does that differ from the market?
4. What materially changed or deserves attention?

Everything else should be progressively disclosed.

The current coherent interface is already pointed in the right direction: one official forecast is visually dominant, football and market signals are distinct, lifecycle/lock state is explicit, and advanced methodology is lower in the hierarchy. The next phase should refine that hierarchy rather than add more panels to the front door.

## Current product audit

### What is already strong

- **One official probability.** The game card and modal consistently lead with LevLine's winner and probability.
- **Market is context, not a second forecast.** The card explicitly states the probability-point difference and the modal separates football, market and official signals.
- **Immutable-state language is visible.** LIVE FORECAST / FINAL PREGAME / IN PROGRESS / GRADED prevents a post-kickoff refresh from pretending to be the original call.
- **Methodology is progressively disclosed.** Technical formula details are not forced into the default game-reading flow.
- **Source-linked developments.** Context can be inspected without claiming that every news item altered the model.
- **Responsive baseline.** The current release has dedicated desktop/tablet/mobile browser checks.

### Friction to investigate

#### 1. The weekly card still asks the user to parse too much

The current card includes official probability, interpretation sentence, probability-implied line, approximate score, market line/probability, LevLine-vs-market delta, latest signal and lifecycle metadata. None is individually unreasonable, but together they compete with the primary forecast.

**Research direction:** create a simpler scan layer:

- matchup + kickoff + lifecycle;
- **LevLine winner + probability** as the dominant object;
- market delta immediately adjacent (for example `+3.3 pp vs market`);
- one compact `What changed` line;
- line/score/context below a disclosure boundary or in the game view.

The probability-implied line should not receive equal visual weight with the validated winner probability because Phase 3B did not validate it as expected margin.

#### 2. The modal should behave like a game dossier

The current modal is rich but primarily linear. The next version should establish a stable information order:

**Forecast → What changed → Market comparison → Personnel/weather context → Movement → Model diagnostics → methodology/provenance.**

On mobile, pin a compact game header containing teams, official probability and lock/lifecycle state while the user scrolls.

#### 3. “What changed?” should become a first-class product object

A user returning to the same game should not have to compare charts manually. LevLine should generate a factual delta summary such as:

- official probability moved 2.1 pp since the prior refresh;
- market moved 1.4 pp in the same direction;
- starter/depth state changed at 10:00 UTC;
- NWS wind forecast increased from 9 to 17 mph;
- forecast is now immutable; later context did not alter the receipt.

The system must distinguish correlation/timing from causation. A context event can be shown alongside movement without claiming that it caused the movement.

#### 4. Freshness should be per-source, not only per-page

The header currently exposes feed freshness, but advanced public trust will improve if each game can expose a compact **Data as of** drawer:

- LevLine generated time;
- market snapshot time and book count;
- football-data last completed game / last refresh;
- depth/roster snapshot time;
- injury/context snapshot time;
- weather forecast issuance/retrieval time;
- degraded/missing source states.

A stale source should look intentionally stale, not silently normal.

#### 5. History should graduate from record to forecast accountability

The existing History view emphasizes immutable receipts and winner accuracy. Add a dedicated **Calibration / Accountability** layer that treats probability quality as the main outcome:

- Brier and log loss for eligible graded locks;
- reliability/calibration buckets with sample sizes;
- expected vs actual win rate by probability band;
- market comparison on the exact same locked games where a valid market snapshot exists;
- filters by week, probability band and lifecycle;
- receipt detail showing the exact locked forecast and source timestamps.

Avoid leaderboards or “hot streak” framing that incentivize interpreting a small sample as model proof.

#### 6. Teams and Power need clearer jobs

`Power` is team strength; `Forecasts` are matchup probabilities. Make that distinction explicit in copy and navigation.

A future team dossier can make `Teams` more useful:

- power trend;
- recent offense/defense process state;
- current QB / depth-chart snapshot;
- major current personnel context;
- upcoming forecast;
- recent immutable LevLine receipts.

Only validated/sourceable fields should appear. Do not backfill a missing player-impact model with fantasy-style player projections.

#### 7. Public kickoff time should not be hard-coded to Los Angeles

The current frontend formats times in `America/Los_Angeles`. That is convenient for the project owner but wrong as a public default.

Research recommendation: display browser-local time by default with a small `ET`/`Local` toggle, or show local time plus ET in game detail. Persist the user's choice locally; no account is needed.

#### 8. URLs should be shareable

Current tab/modal state is client state rather than a durable URL. A forecast product benefits from direct links:

- `/week/1`
- `/game/2026_01_DEN_KC`
- `/history`
- `/teams/KC`
- `/methodology`

A shared game URL should reopen the exact game dossier and preserve browser back behavior. This is also valuable for social sharing and auditability.

#### 9. Load only what the current view needs

The app currently fetches forecast payloads plus run history, contextual evidence, previews, power ratings, model leaderboard, prediction history, profiles, autopsies, editorial data, raw current rows and impact context in one initial `Promise.all`.

Research recommendation: make `public_forecasts.json` + minimal status the first paint. Lazy-load game-history/evidence when a game opens and lazy-load Teams/Power/History/Methodology datasets when those tabs are visited. This should reduce mobile startup cost and make source failures more isolated.

#### 10. In-progress games need an unmistakable “pregame receipt” frame

Once kickoff occurs, the official LevLine probability should be labeled **Final pregame forecast** rather than visually resembling a live win-probability model. If a live score/status is later added, it must sit beside—not overwrite—the locked pregame forecast.

## Visual / interaction principles

### Forecast-first hierarchy

A mature forecast interface can be visually sophisticated without becoming dense. Historical FiveThirtyEight game cards are useful because the percentage is immediately scannable; ESPN's matchup predictor similarly makes the probability the dominant visual object. LevLine should preserve its own visual identity while borrowing that clarity rather than their exact presentation.

### Progressive disclosure

Advanced numbers, movement charts, source ledgers and component diagnostics are valuable to expert users but should not compete with the primary forecast. Keep the weekly board sparse and make the game dossier the analytical workspace.

### Explain uncertainty; do not invent confidence labels

Avoid categorical labels like HIGH / SOLID / COIN FLIP unless they are separately validated. The probability itself is the confidence statement. Calibration history can teach users what a 60% or 70% forecast has meant historically.

### Avoid sportsbook mimicry

No bet buttons, EV badges, “best bets,” green/red profit colors or pseudo-certainty. Market information is a benchmark and information source.

### Accessibility

- never encode forecast direction or lifecycle only by color;
- all charts need textual equivalents;
- modal/game dossier needs correct dialog semantics, focus management and keyboard escape behavior;
- support reduced motion;
- maintain readable contrast for muted timestamps/source text;
- make touch targets comfortably usable at 320–390 px widths.

## Product concepts to prototype after the current release

### Prototype A — Scan-first week board

Test a reduced card with only official probability, market difference and one change/context line above the fold. Measure whether a user can answer “who does LevLine like and how much?” faster without losing trust.

### Prototype B — Game dossier v2

Build a full-page/deep-link game route with a sticky forecast header and sections for What Changed, Comparison, Context, Movement, Advanced Numbers and Sources.

### Prototype C — Accountability page

Add calibration/reliability and Brier/log-loss reporting to immutable receipts, with clear sample-size warnings.

### Prototype D — Source-health drawer

Show freshness and degraded states per source. This is especially important as Phase 6 adds independently refreshed roster, player-status, weather and multi-book market feeds.

### Prototype E — Team dossier

Turn the current Teams view into a useful football-state page without creating a second prediction model.

## UX research acceptance criteria

A front-facing change should be considered an improvement only if it:

- makes the official probability easier, not harder, to identify;
- cannot create a second competing official forecast;
- preserves lock provenance and lifecycle semantics;
- clearly distinguishes model input, contextual evidence and source-observed information;
- works at 320 px through desktop widths;
- is keyboard-accessible;
- handles missing/stale feeds intentionally;
- avoids materially increasing first-paint data requirements;
- does not imply the probability-implied line is a validated expected-margin forecast.

## Recommended sequence

1. Finish and deploy the current coherent release unchanged.
2. Capture baseline screenshots/performance/accessibility behavior from the deployed site.
3. Prototype scan-first cards and route-based game dossiers on isolated UI branches using the same canonical forecast contract.
4. Add source-freshness and `What changed` contracts before decorating them visually.
5. Add accountability/calibration views once enough graded immutable locks exist to make the display meaningful.
6. Run responsive, keyboard, missing-data and stale-data browser tests before any front-facing merge.

The next UI phase should improve **information architecture first, decoration second**.
