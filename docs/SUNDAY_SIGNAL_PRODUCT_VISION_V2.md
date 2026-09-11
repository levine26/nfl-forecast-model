# Sunday Signal Product Vision V2

Status: design/research only. No production UI authorization is implied.

## Product thesis

Sunday Signal should be the fastest way to answer four questions:

1. Who does LevLine favor?
2. How confident is it?
3. What changed, and why?
4. What could still change before kickoff?

The experience should feel like **a premium Sunday broadcast desk crossed with an analyst's notebook**: energetic and sports-native, but disciplined, legible, and evidence-first. It should not resemble a sportsbook, trading terminal, or generic SaaS dashboard.

## Design principles

### 1. Scan first, investigate second

The week board must be usable in seconds. A user should be able to scan the slate and immediately see:

- matchup and kickoff
- LevLine win probability
- market-implied probability
- model-market disagreement
- forecast movement since the last meaningful lock/update
- key availability/weather flag
- freshness / confidence state

Everything else belongs behind progressive disclosure.

### 2. Probability is the hero, not the pick label

A 54% forecast and an 84% forecast are both "picks" but are not remotely the same information. Probability receives the strongest visual hierarchy. The team pick is secondary.

Use direct numerical probabilities plus a simple part-to-whole or horizontal probability visual where it improves comprehension. Avoid gauges whose angle/area obscures the number.

### 3. Explain movement as a story

Every dossier should have a chronological "Signal Timeline":

- opening / first captured forecast
- market move
- injury/practice-status revision
- starter/depth-chart change
- weather/roof update
- final lock

Each event should answer "what changed" and "how much did LevLine move". This turns provenance into a user-facing feature rather than back-office metadata.

### 4. Separate known, estimated, and missing

The UI must distinguish:

- confirmed fact
- model estimate
- uncertain/probabilistic status
- unavailable source
- stale source

Never silently render missing context as zero or neutral.

### 5. Make uncertainty useful

Use plain-language uncertainty states such as:

- Stable signal
- Lean
- High disagreement
- Personnel-sensitive
- Weather-sensitive
- Data still moving

These labels supplement, never replace, the actual probabilities and source freshness.

### 6. Reward curiosity without creating clutter

Advanced users should be able to drill into calibration, model/market decomposition, personnel impact, movement attribution, source receipts, and methodology. Casual users should never be forced through those layers.

## Visual identity: "Signal Broadcast"

### Core character

Combine three visual references:

- modern NFL broadcast scorebug: quick hierarchy, matchup clarity, live-state energy
- high-quality editorial sports journalism: whitespace, narrative, typography, context
- quantitative notebook: sparklines, small multiples, receipts, restrained technical detail

### Signature motifs

Use these consistently enough that Sunday Signal becomes recognizable:

- **Signal bars** for freshness/strength state, not as a substitute for probability
- **Probability rail** connecting the two teams, with the 50% midpoint visible
- **Movement pulse**: tiny sparkline showing forecast evolution over time
- **Signal Timeline**: event markers tied to movement attribution
- **Why LevLine differs**: a compact decomposition card showing market, pure model, availability/context, and final probability
- **Receipt stamp**: locked timestamp/source state for accountability pages

### Avoid

- neon sportsbook palettes
- fake live tickers with no decision value
- excessive gradients/glassmorphism
- giant donut/gauge charts for binary probability
- dense wall-of-metrics cards
- unexplained acronyms on the week board
- red/green as the only carrier of meaning

## Information architecture

### Week Board

Primary surface. Each game row/card should contain only the information necessary to decide whether the game deserves attention.

Recommended hierarchy:

1. kickoff + network/state
2. away @ home
3. probability rail with exact percentages
4. model edge vs market
5. movement pulse / change since prior lock
6. one-line "Signal" explanation
7. freshness/status chips

Sort/filter modes:

- kickoff time
- largest LevLine edge
- highest confidence
- biggest movement
- most uncertain
- favorite team

### Game Dossier

Order sections by user value:

1. Forecast
2. What Changed
3. Model vs Market
4. Personnel / availability
5. Matchup / process
6. Weather / venue
7. Movement attribution
8. Distribution / score outlook
9. Advanced model detail
10. Sources & freshness

Keep the forecast summary sticky on desktop and compact-sticky on mobile.

### Accountability

Treat accountability as a first-class product, not a methodology appendix.

Show:

- immutable pregame receipt
- forecast at lock
- result after completion
- Brier contribution / calibration bucket where appropriate
- model vs market comparison
- cumulative score trends
- no hindsight rewriting

This is a differentiator: users should be able to inspect exactly what Sunday Signal believed before kickoff.

### Methodology

Use layered disclosure:

- 30-second explanation
- 5-minute explanation
- full technical methodology

A nontechnical user should understand that LevLine combines historical team strength, market information, and verified pregame context without needing to know the full stacking implementation.

## Probability communication

Human-factors literature supports clear numerical probabilities and simple visual aids, while also cautioning that graphics can mislead when the encoded quantity is ambiguous. For Sunday Signal:

- always print the number
- use a common 0-100 probability scale across games
- make the 50% reference obvious
- reserve line charts for change over time
- use part-to-whole/icon concepts sparingly, mainly in onboarding/methodology rather than every game card
- do not translate 63% into words like "likely" without retaining 63%

## Interaction design

### Desktop

- dense but breathable week board
- hover/focus preview with top movement driver
- keyboard navigation between games
- right-side or full-page dossier, depending viewport

### Mobile

- one-thumb week board
- probability and teams visible without horizontal scrolling
- compact chips, not mini tables
- dossier sections collapsible but deep-linkable
- sticky forecast summary

### State handling

Every route needs explicit states for:

- loading
- partial data
- stale data
- source failure
- forecast locked
- game started
- game final

Never flash empty values that look authoritative.

## Front-end performance and accessibility

- route-scoped/lazy analytical payloads
- avoid loading full historical data on the week board
- performance budgets for JS and initial data payload
- semantic headings/landmarks
- visible keyboard focus
- skip link
- WCAG-compliant contrast
- reduced-motion behavior
- no information communicated by color alone
- deterministic time-zone display with clear PT/ET/local control

## Proposed user-facing features

### "Why this game matters"

One sentence generated from structured evidence, e.g. the largest model-market disagreement, biggest lineup sensitivity, or most meaningful movement.

### "Since you last checked"

Browser-local comparison of probability, market, injury, and weather changes since the user's previous visit. This should remain client-side and should never alter official forecast history.

### "Signal Score"

Do not create a mysterious composite score. If used at all, it must be a transparent presentation-only label derived from already-published dimensions such as model-market disagreement, forecast stability, and source freshness. It must not become a hidden predictive feature.

### "What would change my mind"

For uncertain games, surface one or two known sensitivities: e.g. QB designation, OL starter availability, or wind threshold. This can make the product feel intelligent without pretending to predict unavailable facts.

## Research references and patterns reviewed

- FiveThirtyEight NFL/MLB/NBA prediction interactives: probability-first presentation, simulation, current vs full-strength state, explicit methodology/versioning.
- ESPN-style win-probability presentation: familiar sports-native score/game context paired with a simple probability trend.
- Human-factors risk communication literature: exact numbers plus appropriately chosen bars/part-to-whole visuals improve gist, but visualization format must match the communication task.
- Current independent sports analytics dashboards: useful for interaction and card-layout ideas, but Sunday Signal should avoid copying sportsbook visual language.

## Prototype plan

1. Preserve current draft/non-production branch posture.
2. Build one high-fidelity Week Board using real current schema.
3. Build one Game Dossier with real source/freshness/error states.
4. Add movement timeline and model-vs-market decomposition.
5. Add mobile sticky forecast summary.
6. Run Playwright at desktop/tablet/mobile widths plus keyboard/accessibility checks.
7. Add performance budgets and lazy-loading assertions.
8. Conduct a heuristic audit against five tasks:
   - identify strongest pick in <10 seconds
   - identify biggest model-market disagreement in <10 seconds
   - understand why a forecast moved in <20 seconds
   - verify freshness/source state in <20 seconds
   - inspect accountability receipt without reading methodology
9. Keep prototype unmerged until explicit production-design authorization.

## Success criteria

Sunday Signal V2 succeeds when a first-time user can understand the slate without instruction, while an expert can inspect the exact model/data story behind every forecast. It should look unmistakably like Sunday Signal, remain fast on mobile, communicate probabilities honestly, and make LevLine's provenance/accountability advantage visible rather than hidden.
